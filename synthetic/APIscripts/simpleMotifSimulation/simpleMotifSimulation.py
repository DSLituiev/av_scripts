#!/usr/bin/env python
import os;
import sys;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter
import util;
from synthetic import synthetic;
import argparse;

def do(options):
    outputFileName_core = util.addArguments("singleMotifSim"
        , [util.BooleanArgument(options.bestHit, "bestHit")
         , util.ArgumentToAdd(options.motifName, "motif")
         , util.ArgumentToAdd(options.motifProb, "motifProb")
         , util.ArgumentToAdd(options.seqLength, "seqLength")
         , util.ArgumentToAdd(options.numSeqs, "numSeqs")]);
    
    loadedMotifs = synthetic.LoadedEncodeMotifs(options.pathToMotifs, pseudocountProb=0.001)
    Constructor = synthetic.BestHitPwmFromLoadedMotifs if options.bestHit else synthetic.PwmSamplerFromLoadedMotifs;  
 
    embedInBackground = synthetic.EmbedInABackground(
        backgroundGenerator=synthetic.ZeroOrderBackgroundGenerator(seqLength=options.seqLength) 
        , embedders= [
            synthetic.RepeatedEmbedder(
                embedder=synthetic.SubstringEmbedder(
                    substringGenerator=Constructor(
                       loadedMotifs=loadedMotifs                  
                        ,motifName=options.motifName 
                    )
                    ,positionGenerator=synthetic.UniformPositionGenerator())
                ,quantityGenerator=synthetic.BernoulliQuantityGenerator(prob=options.motifProb))
        ]
    );
    loadedMotifs = synthetic.LoadedEncodeMotifs(options.pathToMotifs, pseudocountProb=0.001);

    sequenceSet = synthetic.GenerateSequenceNTimes(embedInBackground, options.numSeqs)
    synthetic.printSequences(outputFileName_core+".simdata", sequenceSet, includeFasta=True, includeEmbeddings=True);

if __name__=="__main__":
    parser = argparse.ArgumentParser();
    parser.add_argument("--pathToMotifs", default="motifs.txt");
    parser.add_argument("--bestHit", action="store_true");
    parser.add_argument("--motifName", required=True);
    parser.add_argument("--seqLength", type=int, required=True);
    parser.add_argument("--numSeqs", type=int, required=True);
    parser.add_argument("--motifProb", type=float, default=1.0);
    options = parser.parse_args();
    do(options);     
