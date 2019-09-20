# Copytight (C) Meilof Veeningen, 2019

from .runtime import guarded, is_base_value, PubVal, PrivVal, ignore_errors, is_base_value, LinComb

import inspect
    
def if_then_else(cond, truev, falsev):
    if truev is falsev: return truev
    
    if is_base_value(cond):
        if cond!=0 and cond!=1: 
            raise ValueError("not a boolean value: " + str(cond))
        return truev if cond else falsev
    elif (not ignore_errors) and cond.value!=0 and cond.value!=1:
        raise(ValueError("not a bit: " + str(cond)))
    else:
        if callable(truev): truev = guarded(cond)(truev)()
        if callable(falsev): falsev = guarded(1-cond)(falsev)()        
 
        if isinstance(truev, list):
            return [if_then_else(cond, truevi, falsevi) for (truevi,falsevi) in zip(truev,falsev)]
        elif is_base_value(truev) or isinstance(truev, LinComb):
            return falsev+cond*(truev-falsev)
        else:
            return truev.__if_then_else__(falsev, cond)

def _if(cond, returns=None, globmod=None, globvars=None):
    def __if(fn):
        # globals
        nonlocal returns, globmod, globvars
        if globmod is None: globmod = inspect.getmodule(fn)
        if globvars is None: globvars = inspect.getclosurevars(fn).globals
        globbak = {nm:getattr(globmod,nm) for nm in globvars}
        
        # locals
        defs = inspect.getargspec(fn).defaults
        if defs is None:
            if returns is None: returns=dict()
        elif len(defs)==1 and isinstance(defs[0],dict):
            returns=defs[0]
        else:
            raise ArgumentError("Incorrect defaults: " + str(defs))
        retbak = returns.copy()

        myex = None
        
        try:
            # run function
            if defs is None:
                ret = guarded(cond)(fn)()
            else:
                ret = guarded(cond)(fn)(returns)
        except Exception as exc:
            myex = exc
        
        # update modified globals
        for nm in globvars:
            cur = getattr(globmod,nm)
            if not cur is globbak[nm]:
                setattr(globmod,nm,if_then_else(cond, cur, globbak[nm]))
                
        # update modified locals
        for nm in returns:
            if not nm in retbak or retbak[nm] is None:
                raise ArgumentError("Return value set, but no default given: " + str(nm))
            if not returns[nm] is retbak[nm]:
                returns[nm]=if_then_else(cond, returns[nm], retbak[nm])
        
        if myex is not None: raise myex
        return ret if not ret is None else returns
    return __if

def _while(fn):
    if inspect.getargspec(fn).defaults is not None:
        freturns = inspect.getargspec(fn).defaults[0]
    else:
        freturns = None
    fglobs = inspect.getclosurevars(fn).globals
    fmod = inspect.getmodule(fn)
    gen=fn()
    guard = next(gen)
        
    try:
        while True:
            cond = _if(guard, returns = freturns, globmod=fmod, globvars=fglobs)(lambda: next(gen))
            guard = guard*cond
    except StopIteration:
        pass
    
    return freturns

__ifelse_stack = []

def _ifelse(cond):
    def __ifelse(fn):
        global __ifelse_stack
        returns = _if(cond)(fn)
        __ifelse_stack.append((1-cond,returns))
        return returns
    return __ifelse

def _elseif(cond):
    global __ifelse_stack
    (acond,areturns)=__ifelse_stack[-1]
    if callable(cond): cond = guarded(acond)(cond)()
    __ifelse_stack[-1] = (acond&(1-cond),areturns)
    return _if(acond&cond, returns=areturns)

def _else(fn):
    global __ifelse_stack
    (acond,areturns)=__ifelse_stack.pop()
    return _if(acond, returns=areturns)(fn)
