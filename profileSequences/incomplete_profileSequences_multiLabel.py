#!/srv/gs1/software/python/python-2.7/bin/python
import sys;
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import fileProcessing as fp;
import util;
import stats;

def main():
    parser = argparse.ArgumentParser(description="Profiles the sequences");
    parser.add_argument('inputFiles',nargs='+');
    parser.add_argument('--outputFile',help="If not specified, name will be 'profiledDifferences_inputFile'");
    parser.add_argument('--tabDelimitedOutput', action="store_true");
    parser.add_argument('--significanceThreshold',type=float,default=0.01);
    parser.add_argument('--progressUpdate',type=int);
    parser.add_argument('--hasNoTitle',action="store_true");
    parser.add_argument('--groupByColIndex',type=int);
    parser.add_argument('--sequencesColIndex',type=int,required=True);
    parser.add_argument('--baseCount', action='store_true');
    parser.add_argument('--gcContent', action='store_true');
    parser.add_argument('--lowercase', action='store_true');
    parser.add_argument('--kmer', type=int);
    args = parser.parse_args();
    profileSequences(args);    

def profileSequences(args):
    countProfilerFactories = [];
    if (args.kmer is not None):
        countProfilerFactories.append(KmerCountProfilerFactory(lambda x: x.upper(), args.kmer));
    if (args.lowercase):
        countProfilerFactories.append(getLowercaseCountProfilerFactory());
    if (args.gcContent):
        countProfilerFactories.append(getGcCountProfilerFactory());
    if (args.baseCount):
        countProfilerFactories.append(getBaseCountProfilerFactory());
    
    (profilerNameToCategoryCountsMap,blah) = profileInputFile(
            args.inputFiles
            , countProfilerFactories
            , categoryFromInput=((lambda x: x[args.groupByColIndex]) if (args.groupByColIndex is not None) else (lambda x: "defaultCategory"))
            , sequenceFromInput=(lambda x: x[args.sequencesColIndex])
            , preprocessing = util.chainFunctions(fp.trimNewline,fp.splitByTabs)
            , progressUpdate=args.progressUpdate
            , ignoreInputTitle=(not (args.hasNoTitle))
        );
    significantDifferences = computeSignificantDifferences(
        profilerNameToCategoryCountsMap    
        , args.significanceThreshold);
    
    toPrint = "";
    for category in significantDifferences:
        if (args.tabDelimitedOutput == False):
            toPrint = toPrint + "-----\n" + category + ":\n-----\n";
        if (args.tabDelimitedOutput):
            toPrint += SignificantResults.tabTitle()+"\n";
        toPrint = toPrint + "\n".join([x.tabDelimString() if args.tabDelimitedOutput else str(x) for x in significantDifferences[category]])+"\n";
    
    if (args.outputFile is None):
        args.outputFile = fp.getFileNameParts(args.inputFiles[0]).getFilePathWithTransformation(lambda x: 'profiledDifferences_'+x, '.txt');
        
    fp.writeToFile(args.outputFile, toPrint);
    

def profileInputFile(inputFiles
    , countProfilerFactories
    , idxByTask_categoryFromInput
    , sequenceFromInput
    , preprocessing=None
    , filterFunction=None
    , transformation=lambda x: x
    , progressUpdate=None
    , ignoreInputTitle=False
    , tasks=["defaultTask"]):
    #init map of count profiler name to map of category-->count
    idxByTask_profilerName_to_categoryToCountMaps = [{} for task in tasks];
    idxByTask_categoryCounts = [{} for task in tasks];    
    def action(input,i): #the input is the value of the line after preprocess, filter and transformation
        idxByTask_category = idxByTask_categoryFromInput(input);
        sequence = sequenceFromInput(input);
        for (taskIdx, category) in enumerate(idxByTask_category):
            categoryCounts = idxByTask_categoryCounts[taskIdx];
            profilerName_to_categoryToCountMaps = idxByTask_profilerName_to_categoryToCountMaps[taskIdx];
            if (category not in categoryCounts):
                categoryCounts[category] = 0;
            categoryCounts[category] += 1;
            for countProfilerFactory in countProfilerFactories:
                if (countProfilerFactory.profilerName not in profilerName_to_categoryToCountMaps):
                    profilerName_to_categoryToCountMaps[countProfilerFactory.profilerName] = {}
                if (category not in profilerName_to_categoryToCountMaps[countProfilerFactory.profilerName]):
                    profilerName_to_categoryToCountMaps[countProfilerFactory.profilerName][category] = countProfilerFactory.getCountProfiler();
                profilerName_to_categoryToCountMaps[countProfilerFactory.profilerName][category].process(sequence);
    
    for inputFile in inputFiles:
        print "Processing",inputFile;
        inputFileHandle = fp.getFileHandle(inputFile);
        fp.performActionOnEachLineOfFile(
            inputFileHandle
            ,action
            ,preprocessing=preprocessing
            ,filterFunction=filterFunction
            ,transformation=transformation
            ,ignoreInputTitle=ignoreInputTitle
            ,progressUpdate=progressUpdate
        );
    return profilerName_to_categoryToCountMaps,categoryCounts;        


#to be used in conjunction with output of profileInputFile
def computeSignificantDifferences(
        profilerName_to_categoryToCountMaps
        ,significanceThreshold=0.01
    ):
    significantDifferences = {};
    for profilerName in profilerName_to_categoryToCountMaps:
        print "Profiling: "+profilerName;
        categoryCountMap = profilerName_to_categoryToCountMaps[profilerName];
        significantDifferences[profilerName] = profileCountDifferences(categoryCountMap,significanceThreshold);
    return significantDifferences;    
    

class CountProfiler:
    def __init__(self,profilerName):
        self.counts = {};
        self.profilerName = profilerName;
        self.sequencesProcessed = 0;
    def incrementSequencesProcessed(self):
        self.sequencesProcessed += 1;
    def incrementKey(self, key):
        if (key not in self.counts):
            self.counts[key] = 0;
        self.counts[key] += 1;
    def normalise(self):
        total = 0;
        for aKey in self.counts:
            total += self.counts[aKey];
        self.total = total;
        self.normalisedCounts = {};
        for aKey in self.counts:
            self.normalisedCounts[aKey] = float(self.counts[aKey])/total;
        return self.normalisedCounts;

def getLetterByLetterKeysGenerator(letterToKey):
    def letterByLetterKeysGenerator(sequence):
        for letter in sequence:
            yield letterToKey(letter);
    return letterByLetterKeysGenerator;

def getLowercaseCountKeysGenerator():
    lowercaseAlphabet = ['a','c','g','t']
    uppercaseAlphabet = ['A','C','G','T']
    def letterToKey(x):
        if (x in lowercaseAlphabet):
            return 'acgt';
        if (x in uppercaseAlphabet):
            return 'ACGT';
        if (x == 'N'):
            return 'N';
        raise Exception("Unexpected dna input: "+x);
    return getLetterByLetterKeysGenerator(letterToKey);

def getGcCountKeysGenerator():
    cgArr = ['c','g','C','G'];
    atArr = ['a','t','A','T'];
    def letterToKey(x):
        if (x in cgArr):
            return 'GC';
        if (x in atArr):
            return 'AT';
        if (x == 'N'):
            return 'N';
        raise Exception("Unexpected dna input: "+x);
    return getLetterByLetterKeysGenerator(letterToKey);

def getBaseCountKeysGenerator():
    return getLetterByLetterKeysGenerator(lambda x: x.upper());

def getKmerGenerator(stringPreprocess,kmerLength):
    def keysGenerator(sequence):
        sequence = stringPreprocess(sequence);
        #not the best rolling window but eh:
        for i in range(0,len(sequence)-kmerLength+1):
            yield sequence[i:i+kmerLength];
    return keysGenerator;
    
#tests for significant differences. Assumes a multinomial model.
def profileCountDifferences(mapOfCategoryToCountProfiler #category is the overall class, count profiler tracks the features associated with that class.
                            ,significanceThreshold=0.01):

    significantResults = [];
    keyTotals = {}; #'key' is the feature that's significantly enriched
    grandTotal = 0; #the total number of observed features (recall, assuming a multinomial model)
    for category in mapOfCategoryToCountProfiler: #iterate over every category/class
        mapOfCategoryToCountProfiler[category].normalise(); #normalise the counts for that category
        counts = mapOfCategoryToCountProfiler[category].counts;
        grandTotal += mapOfCategoryToCountProfiler[category].total;
        for key in counts:
            if key not in keyTotals:
                keyTotals[key] = 0;
            keyTotals[key] += counts[key];
    #performing the hypgeo test:
    for category in mapOfCategoryToCountProfiler:
        print("Profiling differences for "+category);
        counts = mapOfCategoryToCountProfiler[category].counts;
        for key in counts:
            special = keyTotals[key];
            picked = mapOfCategoryToCountProfiler[category].total;
            specialPicked = counts[key];
            testResult = stats.proportionTest(grandTotal,special,picked,specialPicked);
            if (testResult.pval <= significanceThreshold):
                significantResults.append(SignificantResults(grandTotal,special,picked,specialPicked,testResult,key,category));
    return significantResults;

class SignificantResults:
    def __init__(self,total,special,picked,specialPicked,testResult,specialName="special",pickedName="picked"):
        self.total = total;
        self.special = special;
        self.picked = picked;
        self.specialPicked = specialPicked;
        self.testResult = testResult;
        self.specialName = specialName;
        self.pickedName = pickedName;
        self.pickedRatio = 0 if self.picked == 0 else float(self.specialPicked)/self.picked;
        self.specialUnpicked = self.special-self.specialPicked;
        self.unpicked = self.total - self.picked;
        self.unpickedRatio = 0 if self.unpicked == 0 else float(self.specialUnpicked)/self.unpicked;
    def __str__(self):
        pickedRatio = float(self.specialPicked)/self.picked;
        unpickedRatio = 0 if self.total == self.picked else float(self.special-self.specialPicked)/(self.total - self.picked);
        return self.pickedName+" for "+self.specialName+" - "+str(pickedRatio)+" vs. "+str(unpickedRatio)+"; "+(str(self.testResult)
            +", "+self.specialName+": "+str(self.special)
            +", "+self.pickedName+": "+str(self.picked)
            +", both: "+str(self.specialPicked)
            +", total: "+str(self.total)); 
    def tabDelimString(self):
        return self.pickedName+"\t"+self.specialName+"\t"+self.testResult.tabDelimString()+"\t"+str(self.pickedRatio)+"\t"+str(self.unpickedRatio)+"\t"+str(self.specialPicked)+"\t"+str(self.picked)+"\t"+str(self.specialUnpicked)+"\t"+str(self.unpicked);
    @staticmethod
    def tabTitle():
        return "pickedName\tspecialName\t"+stats.TestResult.tabTitle()+"\tpickedRatio\tunpickedRatio\tspecialPicked\tpicked\tspecialUnpicked\tunpicked";

if __name__ == "__main__":
    main();




