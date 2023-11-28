import flatbuffers
import math
import sys
from spzk import main_spzk 

import pysnark.gmpy as gmpy

import pysnark.zkinterface.BilinearConstraint as BilinearConstraint
import pysnark.zkinterface.CircuitHeader as CircuitHeader
import pysnark.zkinterface.Message as Message
import pysnark.zkinterface.ConstraintSystem as ConstraintSystem
import pysnark.zkinterface.Root as Root
import pysnark.zkinterface.Variables as Variables
import pysnark.zkinterface.Witness as Witness



modulus=21888242871839275222246405745257275088548364400416034343698204186575808495617
BL=math.ceil(modulus.bit_length()/8)

def set_modulus(new_modulus):
	global modulus, BL
	modulus = new_modulus
	BL=math.ceil(modulus.bit_length()/8)

class LinearCombination:
    def __init__(self, lc): self.lc = lc
    def __add__(self, other):
        lc = dict()
        for a in self.lc:
            if a in other.lc:
                lc[a] = self.lc[a] + other.lc[a]
            else:
                lc[a] = self.lc[a]
        for b in other.lc:
            if not b in self.lc:
                lc[b] = other.lc[b]
        return LinearCombination(lc)
    
    def __sub__(self, other):
        return self+(-other)
    
    def __mul__(self, other):
        return LinearCombination({key:value*other for (key,value) in self.lc.items()})

    def __neg__(self):
        return self*-1

privvals = []
    
def privval(val):
    privvals.append(val)
    return LinearCombination({-len(privvals):1})

pubvals = []

def pubval(val):
    pubvals.append(val)
    return LinearCombination({len(pubvals):1})

def zero():
    return LinearCombination({})
    
def one():
    return LinearCombination({0:1})

def fieldinverse(val):
    return int(gmpy.invert(val, modulus))

def get_modulus():
    return modulus

constraints = []
def add_constraint(v, w, y):
    constraints.append([v,w,y])
    
def write_varlist(builder, vals, offset):
    Variables.VariablesStartVariableIdsVector(builder, len(vals))
    for i in reversed(range(len(vals))):
        builder.PrependUint64(i+offset)
    ixs = builder.EndVector()
    
    Variables.VariablesStartValuesVector(builder, BL*len(vals))
    for i in reversed(range(len(vals))):
        val=vals[i]%modulus
        for j in reversed(range(BL)):
            builder.PrependByte((val>>(j*8))&255)
    vals = builder.EndVector()
        
    Variables.VariablesStart(builder)
    Variables.VariablesAddVariableIds(builder, ixs)
    Variables.VariablesAddValues(builder, vals)
    return Variables.VariablesEnd(builder)   
    
    
def prove():
    # TODO: this is pretty slow, maybe use this to improve performance:
    # https://github.com/google/flatbuffers/issues/4668
    
    fh = open('inputs.zkif', 'wb')
    write_input(fh)
    fh.close()

    fcs = open('constraints.zkif', 'wb')
    write_constraints(fcs)
    fcs.close()

    fw = open('witness.zkif', 'wb')
    write_witness(fw)
    fw.close()
    
    print("*** VBG zkinterface constraints, input, witness, written to corresponding .zkif files")

    # circuit_buf = write_circuit()
    # print("curcuit_buf", circuit_buf)

    # witness_buf = write_witness()
    # constaints_buf = write_constraints()
    
    # write_witness(f)
    # write_constraints(f)

    #main_spzk(circuit_buf, constaints_buf, witness_buf)

   

def write_input(f):    
    print("*** VBG zkinterface: writing circuit", file=sys.stderr)
    
    builder = flatbuffers.Builder(1024)

    #create a list of public vals for CircuitHeader 
    vars = write_varlist(builder, pubvals, 1)
    
    CircuitHeader.CircuitHeaderStartFieldMaximumVector(builder, BL)
    for i in reversed(range(BL)):
        builder.PrependByte(((modulus-1)>>(i*8))&255)
    maxi = builder.EndVector()
    
    CircuitHeader.CircuitHeaderStart(builder)
    CircuitHeader.CircuitHeaderAddInstanceVariables(builder, vars)
    CircuitHeader.CircuitHeaderAddFreeVariableId(builder, len(pubvals)+len(privvals)+1)
    #CircuitHeader.CircuitHeaderAddR1csGeneration(builder, True)
    #CircuitHeader.CircuitHeaderAddWitnessGeneration(builder, True)
    CircuitHeader.CircuitHeaderAddFieldMaximum(builder, maxi)
    circ = CircuitHeader.CircuitHeaderEnd(builder)
    
    Root.RootStart(builder)
    Root.RootAddMessageType(builder, Message.Message.CircuitHeader)
    Root.RootAddMessage(builder, circ)
    root = Root.RootEnd(builder)
        
    builder.FinishSizePrefixed(root)
    buf = builder.Output()
    #return buf
    f.write(buf)
    
def write_witness(f):    
    print("*** VBG zkinterface: writing witness", file=sys.stderr)
    
    # build witness
    builder = flatbuffers.Builder(1024)
    
    vars = write_varlist(builder, privvals, len(pubvals)+1)
    
    Witness.WitnessStart(builder)
    Witness.WitnessAddAssignedVariables(builder, vars)
    wit = Witness.WitnessEnd(builder)
    
    Root.RootStart(builder)
    Root.RootAddMessageType(builder, Message.Message.Witness)
    Root.RootAddMessage(builder, wit)
    root = Root.RootEnd(builder)    
    
    builder.FinishSizePrefixed(root)
    buf = builder.Output()
    #return buf
    f.write(buf)    
    
def write_constraints(f):    
    print("*** VBG zkinterface: writing constraints", file=sys.stderr)
    
    builder = flatbuffers.Builder(1024)
    
    def write_lc(lc):
        varls = list(lc.lc.keys())
        
        Variables.VariablesStartVariableIdsVector(builder, len(varls))
        for i in reversed(range(len(varls))):
            varix = varls[i] if varls[i]>=0 else len(pubvals)-varls[i]
            builder.PrependUint64(varix)
        vars = builder.EndVector()
        
        Variables.VariablesStartValuesVector(builder, BL*len(varls))
        for i in reversed(range(len(varls))):
            for j in reversed(range(BL)):
                val=lc.lc[varls[i]]%modulus
                builder.PrependByte((val>>(j*8))&255)
        vals = builder.EndVector()
        
        Variables.VariablesStart(builder)
        Variables.VariablesAddVariableIds(builder, vars)
        Variables.VariablesAddValues(builder, vals)
        return Variables.VariablesEnd(builder)
    
    def write_constraint(c):
        la = write_lc(c[0])
        lb = write_lc(c[1])
        lc = write_lc(c[2])
        
        BilinearConstraint.BilinearConstraintStart(builder)
        BilinearConstraint.BilinearConstraintAddLinearCombinationA(builder, la)
        BilinearConstraint.BilinearConstraintAddLinearCombinationB(builder, lb)
        BilinearConstraint.BilinearConstraintAddLinearCombinationC(builder, lc)
        
        return BilinearConstraint.BilinearConstraintEnd(builder)       
        
    cs = [write_constraint(c) for c in constraints]
    
    ConstraintSystem.ConstraintSystemStartConstraintsVector(builder, len(cs))
    for i in reversed(range(len(cs))):
        builder.PrependUOffsetTRelative(cs[i])
    cvec = builder.EndVector()
    
    ConstraintSystem.ConstraintSystemStart(builder)
    ConstraintSystem.ConstraintSystemAddConstraints(builder, cvec)
    r1cs = ConstraintSystem.ConstraintSystemEnd(builder)
    
    Root.RootStart(builder)
    Root.RootAddMessageType(builder, Message.Message.ConstraintSystem)
    Root.RootAddMessage(builder, r1cs)
    root = Root.RootEnd(builder)    
    
    builder.FinishSizePrefixed(root)
    buf = builder.Output()
    #return buf
    f.write(buf)

