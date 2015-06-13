#!/usr/bin/env python
from __future__ import division;
from __future__ import print_function;
import os, sys;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import util;
import argparse;
from pwm import makePwmSamples;
from pwm import pwm;
import numpy as np;
import random;
import fileProcessing as fp;
import math;
from collections import OrderedDict;

def printSequences(outputFileName, sequenceSetGenerator):
    """
        outputFileName: string
        sequenceSetGenerator: instance of AbstractSequenceSetGenerator

        Given an output filename, and an instance of AbstractSequenceSetGenerator,
        will call the sequence set generator and print the generated sequences
        to the output file. Will also create a file "info_outputFileName.txt"
        in the samedirectory as outputFileName that contains all the information
        about sequenceSetGenerator.
    """
    ofh = fp.getFileHandle(outputFileName, 'w');
    ofh.write("seqName\tsequence\n");
    generatedSequences = sequenceSetGenerator.generateSequences(); #returns a generator
    for generateSequence in generatedSequences:
        ofh.write(generateSequence.seqName+"\t"+generateSequence.seq+"\n");
    ofh.close(); 
    infoFilePath = fp.getFileNameParts(outputFileName).getFilePathWithTransformation(lambda x: "info_"+x, extension=".txt");
    
    import json;
    ofh = fp.getFileHandle(infoFilePath, 'w');
    ofh.write(json.dumps(sequenceSetGenerator.getJsonableObject(), indent=4, separators=(',', ': '))); 
    ofh.close(); 

class GeneratedSequence(object):
    """
        An object representing a sequence that has been
        generated.
    """
    def __init__(self, seqName, seq, embeddings):
        """
            seqName: string
            seq: generated sequence (string)
            embeddings: array of Embedding objects
        """
        self.seqName = seqName;
        self.seq = seq;
        self.embeddings = embeddings;

class Embedding(object):
    """
        Represents something that has been embedded in
        a sequence
    """
    def __init__(self, what, startPos):
        """
            seq: object representing the thing that has been embedded. Should have __str__ defined
            startPos: that position relative to the start of the
            parent sequence at which seq has been embedded
        """
        self.what = what;
        self.startPos = startPos;

class AbstractSequenceSetGenerator(object):
    """
        class that is used to return a generator for a collection
        of generated sequences.
    """
    def generateSequences(self):
        """
            returns a generator of GeneratedSequence objects
        """
        raise NotImplementedError();
    def getJsonableObject(self):
        """
            returns an object representing the details of this, which
            can be converted to json.
        """
        raise NotImplementedError();

class GenerateSequenceNTimes(AbstractSequenceSetGenerator):
    """
        If you just want to use a generator of a single sequence and
        call it N times, use this class.
    """
    def __init__(self, singleSequenceGenerator, N):
        """
            singleSequenceGenerator: an instance of AbstractSingleSequenceGenerator
        """
        self.singleSequenceGenerator = singleSequenceGenerator;
        self.N = N;
    def generateSequences(self):
        """
            calls singleSequenceGenerator N times.
        """
        for i in xrange(self.N):
            yield self.singleSequenceGenerator.generateSequence();
    def getJsonableObject(self):
        return OrderedDict([("numSeq",self.N),("singleSequenceGenerator",self.singleSequenceGenerator.getJsonableObject())]);

class AbstractSingleSequenceGenerator(object):
    """
        When called, generates a single sequence
    """
    def __init__(self, namePrefix=None):
        """
            namePrefix: the GeneratedSequence object has a field for the object's name; this is
            the prefix associated with that name. The suffix is the value of a counter that
            is incremented every time 
        """
        self.namePrefix = namePrefix if namePrefix is not None else "synth";
        self.sequenceCounter = 0;
    def generateSequence(self):
        """
            returns GeneratedSequence object
        """
        raise NotImplementedError(); 
    def getJsonableObject(self):
        """
            returns an object representing the details of this, which
            can be converted to json.
        """
        raise NotImplementedError();

class EmbedInABackground(AbstractSingleSequenceGenerator):
    def __init__(self, backgroundGenerator, embedders, namePrefix=None):
        """
            backgroundGenerator: instance of AbstractBackgroundGenerator
            embedders: array of instances of AbstractEmbedder
            namePrefix: see parent
        """
        super(EmbedInABackground, self).__init__(namePrefix);
        self.backgroundGenerator = backgroundGenerator;
        self.embedders = embedders;
    def generateSequence(self):
        """
            generates a background using self.backgroundGenerator, splits it into an array,
            and passes it to each of self.embedders in turn for embedding things.
            returns an instance of GeneratedSequence
        """
        backgroundString = self.backgroundGenerator.generateBackground();
        backgroundStringArr = [x for x in backgroundString];
        #priorEmbeddedThings keeps track of what has already been embedded
        priorEmbeddedThings = PriorEmbeddedThings_numpyArrayBacked(len(backgroundStringArr));
        for embedder in self.embedders:
            embedder.embed(backgroundStringArr, priorEmbeddedThings);  
        self.sequenceCounter += 1;
        return GeneratedSequence(self.namePrefix+str(self.sequenceCounter), "".join(backgroundStringArr), priorEmbeddedThings.getEmbeddings());
    def getJsonableObject(self):
        """
            see parent
        """
        return OrderedDict([("class", "EmbedInABackground")
                            ,("namePrefix", self.namePrefix)
                            ,("backgroundGenerator",self.backgroundGenerator.getJsonableObject())
                            ,("embedders",[x.getJsonableObject() for x in self.embedders])
                            ]);

class AbstractPriorEmbeddedThings(object):
    """
        clas that is used to keep track of what has already been embedded in a sequence
    """
    def canEmbed(self, startPos, endPos):
        """
            returns a boolean indicating whether the region from startPos to endPos is available for embedding
        """
        raise NotImplementedError();
    def addEmbedding(self, startPos, what):
        """
            embeds "what" from startPos to startPos+len(what). Creates an Embedding object
        """
        raise NotImplementedError();
    def getNumOccupiedPos(self):
        """
            returns the number of posiitons that are filled with some kind of embedding
        """
        raise NotImplementedError();
    def getTotalPos(self):
        """
            returns the total number of positions available to embed things in
        """
        raise NotImplementedError();
    def getEmbeddings(self):
        """
            returns a collection of Embedding objects
        """
        raise NotImplementedError();

class PriorEmbeddedThings_numpyArrayBacked(AbstractPriorEmbeddedThings):
    """
        uses a numpy array where positions are set to 1 if they are occupied,
        to determin which positions are occupied and which are not.
        See parent for more documentation.
    """
    def __init__(self, seqLen):
        self.seqLen = seqLen;
        self.arr = np.zeros(seqLen);
        self.embeddings = [];
    def canEmbed(self, startPos, endPos):
        return np.sum(self.arr[startPos:endPos])==0;
    def addEmbedding(self, startPos, what):
        self.arr[startPos:startPos+len(what)] = 1;
        self.embeddings.append(Embedding(seq=what, startPos=startPos));
    def getNumOccupiedPos(self):
        return np.sum(self.arr);
    def getTotalPos(self):
        return len(self.arr);
    def getEmbeddings(self):
        return self.embeddings;

class AbstractEmbedder(object):
    """
        class that is used to embed things in a sequence
    """
    def embed(self, backgroundStringArr, priorEmbeddedThings):
        """ 
            backgroundStringArr: array of characters representing the background string
            priorEmbeddedThings: instance of AbstractPriorEmbeddedThings.
            modifies: backgroundStringArr to include whatever this class has embedded
        """
        raise NotImplementedError();
    def getJsonableObject(self):
        raise NotImplementedError();

class XOREmbedder(AbstractEmbedder):
    """
        calls exactly one of the supplied embedders
    """
    def __init__(self, embedder1, embedder2, probOfFirst):
        """
            embedder1 & embedder2: instances of AbstractEmbedder
            probOfFirst: probability of calling the first embedder
        """
        self.embedder1 = embedder1;
        self.embedder2 = embedder2;
        self.probOfFirst = probOfFirst;
    def embed(self, backgroundStringArr, priorEmbeddedThings):
        if (random.random() < self.probOfFirst):
            embedder = self.embedder1;
        else:
            embedder = self.embedder2;
        return embedder.embed(backgroundStringArr, priorEmbeddedThings);
    def getJsonableObject(self):
        return OrderedDict([ ("class", "XOREmbedder")
                            ,("embedder1", self.embedder1.getJsonableObject())
                            ,("embedder2", self.embedder2.getJsonableObject())
                            ,("probOfFirst", self.probOfFirst)]);

class RepeatedEmbedder(AbstractEmbedder):
    """
        Wrapper around an embedder to call it multiple times according to sampling
        from a distribution.
    """
    def __init__(self, embedder, quantityGenerator):
        """
            embedder: instance of AbstractEmbedder
            quantityGenerator: instance of AbstractQuantityGenerator
        """
        self.embedder = embedder;
        self.quantityGenerator = quantityGenerator;
    def embed(self, backgroundStringArr, priorEmbeddedThings):
        """
            first calls self.quantityGenerator.generateQuantity(), then calls
            self.embedder a number of times equal to the value returned.
        """
        quantity = self.quantityGenerator.generateQuantity();
        for i in range(quantity):
            self.embedder.embed(backgroundStringArr, priorEmbeddedThings);
    def getJsonableObject(self):
        return OrderedDict([("class", "RepeatedEmbedder"), ("embedder", self.embedder.getJsonableObject()), ("quantityGenerator", self.quantityGenerator.getJsonableObject())]);

class AbstractQuantityGenerator(object):
    """
        class to sample according to a distribution
    """
    def generateQuantity(self):
        """
            returns the sampled value
        """
        raise NotImplementedError();
    def getJsonableObject(self):
        raise NotImplementedError();

class FixedQuantityGenerator(AbstractQuantityGenerator):
    """
        returns a fixed number every time generateQuantity is called
    """
    def __init__(self, quantity):
        """
            quantity: the value to return when generateQuantity is called.
        """
        self.quantity = quantity;
    def generateQuantity(self):
        return self.quantity;
    def getJsonableObject(self):
        return "fixedQuantity-"+str(self.quantity);

class PoissonQuantityGenerator(AbstractQuantityGenerator):
    """
        Generates values according to a poisson distribution
    """
    def __init__(self, mean):
        """
            mean: the mean of the poisson distribution
        """
        self.mean = mean;
    def generateQuantity(self):
        return np.random.poisson(self.mean);  
    def getJsonableObject(self):
        return "poisson-"+str(self.mean);

class MinMaxWrapper(AbstractQuantityGenerator):
    """
        Wrapper that restricts a distribution to only return values between the min and
        the max. If a value outside the range is returned, resamples until
        it obtains a value within the range. Warns if it resamples too many times.
    """
    def __init__(self, quantityGenerator, theMin=None, theMax=None):
        """
            quantityGenerator: samples from the distribution to truncate
            theMin: can be None; if so will be ignored
            theMax: can be None; if so will be ignored.
        """
        self.quantityGenerator=quantityGenerator;
        self.theMin=theMin;
        self.theMax=theMax;
        assert self.quantityGenerator is not None;
    def generateQuantity(self):
        tries=0;
        while (True):
            tries += 1;
            quantity = self.quantityGenerator.generateQuantity();
            if ((self.theMin is None or quantity >= self.theMin) and (self.theMax is None or quantity <= self.theMax)):
                return quantity;
            if (tries%10 == 0):
                print("warning: made "+str(tries)+" at trying to sample from distribution with min/max limits");
    def getJsonableObject(self):
        return OrderedDict([("min",self.theMin), ("max",self.theMax), ("quantityGenerator", self.quantityGenerator.getJsonableObject())]);

class ZeroInflater(AbstractQuantityGenerator):
    """
        Wrapper that inflates the number of zeros returned. Flips a coin; if positive,
        will return zero - otherwise will sample from the wrapped distribution (which may still return 0)
    """
    def __init__(self, quantityGenerator, zeroProb):
        """
            quantityGenerator: the distribution to sample from with probability 1-zeroProb
            zeroProb: the probability of just returning 0 without sampling from quantityGenerator
        """
        self.quantityGenerator=quantityGenerator;
        self.zeroProb = zeroProb
    def generateQuantity(self):
        if (random.random() < self.zeroProb):
            return 0;
        else:
            return self.quantityGenerator.generateQuantity();
    def getJsonableObject(self):
        return OrderedDict([("class", "ZeroInflater"), ("zeroProb", self.zeroProb), ("quantityGenerator", self.quantityGenerator.getJsonableObject())]); 

class SubstringEmbedder(AbstractEmbedder):
    """
        embeds a single generated substring within the background sequence,
        at a position sampled from a distribution. Only embeds at unoccupied
        positions
    """
    def __init__(self, substringGenerator, positionGenerator):
        """
            substringGenerator: instance of AbstractSubstringGenerator
            positionGenerator: instance of AbstractPositionGenerator
        """
        self.substringGenerator = substringGenerator;
        self.positionGenerator = positionGenerator;
    def embed(self, backgroundStringArr, priorEmbeddedThings):
        """
            calls self.substringGenerator to determine the substring to embed. Then
            calls self.positionGenerator to determine the start position at which
            to embed it. If the position is occupied, will resample from
            self.positionGenerator. Will warn if tries to resample too many times.
        """
        substring = self.substringGenerator.generateSubstring();
        canEmbed = False;
        tries = 0;
        while canEmbed==False:
            tries += 1;
            startPos = self.positionGenerator.generatePos(len(backgroundStringArr), len(substring));
            canEmbed = priorEmbeddedThings.canEmbed(startPos, startPos+len(substring));
            if (tries%10 == 0):
                print("Warning: made "+str(tries)+" at trying to embed substring of length "+str(len(substring))+" in region of length "+str(priorEmbeddedThings.getTotalPos())+" with "+str(priorEmbeddedThings.getNumOccupiedPos())+" occupied sites");
        backgroundStringArr[startPos:startPos+len(substring)]=substring;
        priorEmbeddedThings.addEmbedding(startPos, substring);
    def getJsonableObject(self):
        return OrderedDict([("substringGenerator", self.substringGenerator.getJsonableObject()), ("positionGenerator", self.positionGenerator.getJsonableObject())]);

class AbstractPositionGenerator(object):
    """
        Given the length of the background sequence and the length
        of the substring you are trying to embed, will return a start position
        to embed the substring at.
    """
    def generatePos(self, lenBackground, lenSubstring):
        raise NotImplementedError();
    def getJsonableObject(self):
        raise NotImplementedError();

class UniformPositionGenerator(AbstractPositionGenerator):
    """
        samples a start position to embed the substring in uniformly at random;
        does not return positions that are too close to the end of the
        background sequence to embed the full substring.
    """
    def generatePos(self, lenBackground, lenSubstring):
        return sampleIndexWithinRegionOfLength(lenBackground, lenSubstring); 
    def getJsonableObject(self):
        return "uniform";

class InsideCentralBp(AbstractPositionGenerator):
    """
        returns a position within the central region of a background
        sequence, sampled uniformly at random
    """
    def __init__(self, centralBp):
        """
            centralBp: the number of bp, centered in the middle of the background,
            from which to sample the position. Is NOT +/- centralBp around the
            middle (is +/- centralBp/2 around the middle).

            If the background sequence is even and centralBp is odd, the shorter
            region will go on the left.
        """
        self.centralBp = centralBp;
    def generatePos(self, lenBackground, lenSubstring):
        if (lenBackground < self.centralBpToEmbedIn):
            raise RuntimeError("The background length should be atleast as long as self.centralBpToEmbedIn; is "+str(lenBackground)+" and "+str(self.centralBpToEmbedIn)+" respectively");
        startIndexForRegionToEmbedIn = int(lenBackground/2) - int(self.centralBp/2);
        indexToSample = startIndexForRegionToEmbedIn + sampleIndexWithinRegionOfLength(self.centralBp, lenSubstring); 
        return int(indexToSample);
    def getJsonableObject(self):
        return "insideCentral-"+str(self.centralBp);

class OutsideCentralBp(AbstractPositionGenerator):
    """
        Returns a position OUTSIDE the central region of a background sequence,
        sampled uniformly at random. Complement of InsideCentralBp.
    """
    def __init__(self, centralBp):
        self.centralBp = centralBp;
    def generatePos(self, lenBackground, lenSubstring):
        #choose whether to embed in the left or the right
        if random.random() > 0.5:
            left=True;
        else:
            left=False;
        #embeddableLength is the length of the region we are considering embedding in
        embeddableLength = 0.5*(lenBackground-self.centralBp);
        #if lenBackground-self.centralBp is odd, the longer region
        #goes on the left (inverse of the shorter embeddable region going on the left in
        #the centralBpToEmbedIn case
        if (left):
            embeddableLength = math.ceil(embeddableLength);
            startIndexForRegionToEmbedIn = 0;
        else:
            embeddableLength = math.floor(embeddableLength);
            startIndexForRegionToEmbedIn = math.ceil((lenBackground-self.centralBp)/2)+self.centralBp;
        indexToSample = startIndexForRegionToEmbedIn+sampleIndexWithinRegionOfLength(embeddableLength, lenSubstring)
        return int(indexToSample);
    def getJsonableObject(self):
        return "outsideCentral-"+str(self.centralBp);

def sampleIndexWithinRegionOfLength(length, lengthOfThingToEmbed):
    """
        uniformly at random samples integers from 0 to length-lengthOfThingToEmbedIn
    """
    assert lengthOfThingToEmbed <= length;
    indexToSample = int(random.random()*((length-lengthOfThingToEmbed) + 1));
    return indexToSample;

class AbstractSubstringGenerator(object):
    """
        Generates a substring, usually for embedding in a background sequence.
    """
    def generateSubstring(self):
        raise NotImplementedError();
    def getJsonableObject(self):
        raise NotImplementedError();

class ReverseComplementWrapper(AbstractSubstringGenerator):
    """
        Wrapper around a AbstractSubstringGenerator that reverse complements it
        with the specified probability.
    """
    def __init__(self, substringGenerator, reverseComplementProb=0.5):
        """
            substringGenerator: instance of AbstractSubstringGenerator
            reverseComplementProb: probability of reverse complementing it.
        """
        self.reverseComplementProb=reverseComplementProb;
        self.substringGenerator=substringGenerator;
    def generateSubstring(self):
        seq = self.substringGenerator.generateSubstring();
        if (random.random() < self.reverseComplementProb): 
            seq = util.reverseComplement(seq);
        return seq;
    def getJsonableObject(self):
        return OrderedDict([("class", "ReverseComplementWrapper"), ("reverseComplementProb",self.reverseComplementProb), ("substringGenerator", self.substringGenerator.getJsonableObject())]);

class AbstractPwmSubstringGenerator(AbstractSubstringGenerator):
    """
        generates a substring from a PWM. Intended to be subclassed.
    """
    def __init__(self, pwm):
        self.pwm = pwm;

class PwmSampler(AbstractPwmSubstringGenerator):
    """
        samples from the pwm by calling self.pwm.sampleFromPwm
    """
    def generateSubstring(self):
        return self.pwm.sampleFromPwm()[0];
    def getJsonableObject(self):
        return "sample-"+self.pwm.name; 

class PwmSubstringGeneratorUsingLoadedMotifs(AbstractSubstringGenerator):
    """
        simple wrapper/container class that extracts a motifName from an AbstractLoadedMotifs instance
        and presents it to the specified pwmSubstringGeneratorClass.
    """
    def __init__(self, loadedMotifs, motifName, pwmSubstringGeneratorClass):
        """
            loadedMotifs: instance of AbstractLoadedMotifs.
            motifName: the name of the pwm as it exists in loadedMotifs
            pwmSubstringGeneratorClass: any class that is a subclass of AbstractPwmSubstringGenerator. This is
            instantiated using the specified pwm.
        """
        self.loadedMotifs = loadedMotifs;
        self.motifName = motifName;
        self.pwmSubstringGenerator = pwmSubstringGeneratorClass(self.loadedMotifs.getPwm(self.motifName));
    def generateSubstring(self):
        return self.pwmSubstringGenerator.generateSubstring();
    def getJsonableObject(self):
        return OrderedDict([("motifName", self.motifName), ("pwmSubstringGenerator", self.pwmSubstringGenerator.getJsonableObject()), ("loadedMotifs",self.loadedMotifs.getJsonableObject())]);

class PwmSamplerFromLoadedMotifs(PwmSubstringGeneratorUsingLoadedMotifs):
    """
        like PwmSubstringGeneratorUsingLoadedMotifs, but always creates an instance of the PwmSampler class
    """
    def __init__(self, loadedMotifs, motifName):
        super(PwmSamplerFromLoadedMotifs, self).__init__(loadedMotifs, motifName, PwmSampler);

class BestHitPwm(AbstractPwmSubstringGenerator):
    """
        always returns the best possible match to the pwm in question when called
    """
    def generateSubstring(self):
        return self.pwm.bestHit; 
    def getJsonableObject(self):
        return "bestHit-"+self.pwm.name;

class BestHitPwmFromLoadedMotifs(PwmSubstringGeneratorUsingLoadedMotifs):
    """
        like PwmSubstringGeneratorUsingLoadedMotifs, but always creates an instance of the BestHitPwm class
    """
    def __init__(self, loadedMotifs, motifName):
        super(BestHitPwmFromLoadedMotifs, self).__init__(loadedMotifs, motifName, BestHitPwm);

class AbstractLoadedMotifs(object):
    """
        A class that contains instances of pwm.PWM loaded from a file.
        The pwms can be accessed by name.
    """
    def __init__(self, fileName, pseudocountProb=0.0):
        """
            fileName: the path to the file to laod
            pseudocountProb: if some of the pwms have 0 probability for
            some of the positions, will add the specified pseudocountProb
            to the rows of the pwm and renormalise.
        """
        self.fileName = fileName;
        fileHandle = fp.getFileHandle(fileName);
        self.pseudocountProb = pseudocountProb;
        self.recordedPwms = OrderedDict();
        action = self.getReadPwmAction(self.recordedPwms);
        fp.performActionOnEachLineOfFile(
            fileHandle = fileHandle
            ,transformation=fp.trimNewline
            ,action=action
        );
        for pwm in self.recordedPwms.values():
            pwm.finalise(pseudocountProb=self.pseudocountProb);
    def getPwm(self, name):
        """
            returns the pwm.PWM instance with the specified name.
        """
        return self.recordedPwms[name];
    def getReadPwmAction(self, recordedPwms):
        """
            This is the action that is to be performed on each line of the
            file when it is read in. recordedPwms is an OrderedDict that
            stores instances of pwm.PWM
        """
        raise NotImplementedError();
    def getJsonableObject(self):
        return OrderedDict([("fileName", self.fileName), ("pseudocountProb",self.pseudocountProb)]);

class LoadedEncodeMotifs(AbstractLoadedMotifs):
    """
        This class is specifically for reading files in the encode motif
        format - specifically the motifs.txt file that contains Pouya's motifs
    """
    def getReadPwmAction(self, recordedPwms):
        currentPwm = util.VariableWrapper(None);
        def action(inp, lineNumber):
            if (inp.startswith(">")):
                inp = inp.lstrip(">");
                inpArr = inp.split();
                motifName = inpArr[0];
                currentPwm.var = pwm.PWM(motifName);
                recordedPwms[currentPwm.var.name] = currentPwm.var;
            else:
                #assume that it's a line of the pwm
                assert currentPwm.var is not None;
                inpArr = inp.split();
                summaryLetter = inpArr[0];
                currentPwm.var.addRow([float(x) for x in inpArr[1:]]);
        return action;

class AbstractBackgroundGenerator(object):
    """
        Returns the sequence that the embeddings are subsequently inserted into.
    """
    def generateBackground(self):
        raise NotImplementedError();
    def getJsonableObject(self):
        raise NotImplementedError();

class ZeroOrderBackgroundGenerator(AbstractBackgroundGenerator):
    """
        returns a sequence with 40% GC content. Each base is sampled independently.
    """
    def __init__(self, seqLength, discreteDistribution=util.DEFAULT_BASE_DISCRETE_DISTRIBUTION):
        """
            seqLength: the length of the sequence to return
            discereteDistribution: instance of util.DiscreteDistribution
        """
        self.seqLength = seqLength;
        self.discreteDistribution = discreteDistribution;
    def generateBackground(self):
        return generateString_zeroOrderMarkov(length=self.seqLength, discreteDistribution=self.discreteDistribution);
    def getJsonableObject(self):
        return OrderedDict([("class","zeroOrderMarkovBackground"), ("length", self.seqLength), ("distribution", self.discreteDistribution.valToFreq)]);

###
#Older API below...this was just set up to generate the background sequence
###

def getGenerationOption(string): #for yaml serialisation
    return util.getFromEnum(GENERATION_OPTION, "GENERATION_OPTION", string);
GENERATION_OPTION = util.enum(zeroOrderMarkov="zrOrdMrkv");

def getFileNamePieceFromOptions(options):
    return options.generationOption+"_seqLen"+str(options.seqLength); 

def generateString_zeroOrderMarkov(length, discreteDistribution=util.DEFAULT_BASE_DISCRETE_DISTRIBUTION):
    """
        discreteDistribution: instance of util.DiscreteDistribution
    """
    sampledArr = util.sampleNinstancesFromDiscreteDistribution(length, discreteDistribution);
    return "".join(sampledArr);

def generateString(options):
    if options.generationOption==GENERATION_OPTION.zeroOrderMarkov:
        return generateString_zeroOrderMarkov(length=options.seqLength);
    else:
        raise RuntimeError("Unsupported generation option: "+str(options.generationOption));

def getParentArgparse():
    parser = argparse.ArgumentParser(add_help=False);
    parser.add_argument("--generationOption", default=GENERATION_OPTION.zeroOrderMarkov, choices=GENERATION_OPTION.vals);
    parser.add_argument("--seqLength", type=int, required=True, help="Length of the sequence to generate");
    return parser; 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(parents=[getParentArgparse()]);
    parser.add_argument("--numSamples", type=int, required=True);
    options = parser.parse_args(); 

    outputFileName = getFileNamePieceFromOptions(options)+"_numSamples-"+str(options.numSamples)+".txt";
 
    outputFileHandle = open(outputFileName, 'w');
    outputFileHandle.write("id\tsequence\n");
    for i in xrange(options.numSamples):
        outputFileHandle.write("synthNeg"+str(i)+"\t"+generateString(options)+"\n");
    outputFileHandle.close();

     

