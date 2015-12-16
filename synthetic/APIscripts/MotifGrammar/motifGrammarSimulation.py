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
from pwm import pwm;

generationSettings = util.enum(
    allBackground="allBackground" 
    ,singleMotif1="singleMotif1" #embeds first motif
    ,singleMotif2="singleMotif2" #embeds second motif
    ,twoMotifs="twoMotifs" #embeds one of both motifs
    ,twoMotifsFixedSpacing="twoMotifsFixedSpacing" #embeds both motifs with a fixed spacing
    ,twoMotifsVariableSpacing="twoMotifsVariableSpacing" #embeds both motifs with a variable spacing
);

def motifGrammarSimulation(options):
    pc = 0.001;
    bestHit = options.bestHit;
    bestHitMode = options.bestHitMode;
    pathToMotifs = options.pathToMotifs;
    loadedMotifs = synthetic.LoadedEncodeMotifs(pathToMotifs, pseudocountProb=pc)
    motifName1 = options.motifName1;
    motifName2 = options.motifName2;
    seqLength = options.seqLength;
    numSeq = options.numSeq;
    generationSetting = options.generationSetting;
    outputFileName = "motifGrammarSimulation_"+generationSetting+("_bestHit_mode-"+bestHitMode if bestHit else "");
    if (generationSetting is not generationSettings.singleMotif2):
        outputFileName+="_motif1-"+motifName1;
    if (generationSetting is not generationSettings.singleMotif1):
        outputFileName+="_motif2-"+motifName2;
    outputFileName+="_seqLength"+str(seqLength)+"_numSeq"+str(numSeq)+".simdata";

    kwargs={'loadedMotifs':loadedMotifs}
    if (bestHit):
        theClass=synthetic.BestHitPwmFromLoadedMotifs;
        kwargs['bestHitMode']=bestHitMode
    else:
        theClass=synthetic.PwmSamplerFromLoadedMotifs;
        

    motif1Generator=theClass(motifName=motifName1,**kwargs)
    motif2Generator=theClass(motifName=motifName2,**kwargs)
    motif1Embedder=synthetic.SubstringEmbedder(substringGenerator=motif1Generator)
    motif2Embedder=synthetic.SubstringEmbedder(substringGenerator=motif2Generator)

    embedders = [];
    if (generationSetting == generationSettings.allBackground):
        namePrefix="synthNeg";
    else:
        namePrefix="synthPos"
    if (generationSetting == generationSettings.allBackground):
        pass;
    elif (generationSetting in [generationSettings.singleMotif1, generationSettings.twoMotifs, generationSettings.singleMotif2]):
        if (generationSetting == generationSettings.singleMotif1):
            embedders.append(motif1Embedder);
        elif (generationSetting == generationSettings.singleMotif2):
            embedders.append(motif2Embedder);
        elif (generationSetting == generationSettings.twoMotifs):
            embedders.append(motif1Embedder);
            embedders.append(motif2Embedder);
        else:
            raise RuntimeError("Unsupported generation setting: "+generationSetting);
    elif (generationSetting in [generationSettings.twoMotifsFixedSpacing, generationSettings.twoMotifsVariableSpacing]):
        if (generationSetting==generationSettings.twoMotifsFixedSpacing):
            separationGenerator=synthetic.FixedQuantityGenerator(options.fixedSpacingOrMinSpacing);
        elif (generationSetting==generationSettings.twoMotifsVariableSpacing):
            separationGenerator=synthetic.UniformIntegerGenerator(minVal=options.fixedSpacingOrMinSpacing
                                                                    ,maxVal=options.maxSpacing);
        else:
            raise RuntimeError("unsupported generationSetting:"+generationSetting);
        embedders.append(synthetic.EmbeddableEmbedder(
                            embeddableGenerator=synthetic.PairEmbeddableGenerator(
                                substringGenerator1=motif1Generator
                                ,substringGenerator2=motif2Generator
                                ,separationGenerator=separationGenerator
                            )
                        ));
    else:
        raise RuntimeError("unsupported generationSetting:"+generationSetting);
        

    embedInBackground = synthetic.EmbedInABackground(
        backgroundGenerator=synthetic.ZeroOrderBackgroundGenerator(seqLength) 
        , embedders=embedders
        , namePrefix=namePrefix
    );

    sequenceSet = synthetic.GenerateSequenceNTimes(embedInBackground, numSeq)
    synthetic.printSequences(outputFileName, sequenceSet);

    #also call scoreSeq on outputFileName
    from pwm import pwm;
    options = util.enum(motifsFile=pathToMotifs
                    ,pwmName=motifName1
                    ,pseudocountProb=pc
                    ,fileToScore=outputFileName
                    ,scoreSeqMode=pwm.SCORE_SEQ_MODE.continuous
                    ,reverseComplementToo=True
                    ,seqCol=1
                    ,auxillaryCols=[0,1]
                    ,topN=None
                    ,greedyTopN=False);
    from pwm import scoreSeq;
    scoreSeq.scoreSeqs(options,returnScores=False);
    options.pwmName=motifName2;
    scoreSeq.scoreSeqs(options,returnScores=False);

if __name__ == "__main__":
    import argparse;
    parser = argparse.ArgumentParser();
    parser.add_argument("--pathToMotifs", default="motifs.txt");
    parser.add_argument("--motifName1", required=True);
    parser.add_argument("--motifName2", required=True);
    parser.add_argument("--bestHit", action="store_true");
    parser.add_argument("--bestHitMode"
                        , default=pwm.BEST_HIT_MODE.pwmProb
                        , choices=pwm.BEST_HIT_MODE.vals);
    parser.add_argument("--seqLength", type=int, required=True);
    parser.add_argument("--numSeq", type=int, required=True);
    parser.add_argument("--generationSetting"
                        , choices=generationSettings.vals
                        , default=generationSettings.twoMotifsFixedSpacing);
    parser.add_argument("--fixedSpacingOrMinSpacing"
                        , type=int);
    parser.add_argument("--maxSpacing", type=int);
    
    options = parser.parse_args();
    motifGrammarSimulation(options); 
