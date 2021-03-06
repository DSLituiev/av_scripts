#!/usr/bin/env python
import sys;
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import math;
import util;
import fileProcessing as fp;
import profileSequences as ps;

def trainNaiveBayes(options,kmerGenerator):
    trainingFile = fp.getFileHandle(options.trainingFile);
    naiveBayesLearner = NaiveBayesLearner();
    def action(inp,lineNumber): #to be performed on each line of the training file
        if (lineNumber%options.progressUpdate == 0):
            print "Processed "+str(lineNumber)+" lines of training file";
        sequence = inp[options.sequenceColIndex].upper();
        if ('N' not in sequence):
            category = inp[options.categoryColIndex];
            naiveBayesLearner.processInput(category, kmerGenerator(sequence));
    fp.performActionOnEachLineOfFile(trainingFile, action=action, ignoreInputTitle=True, transformation=util.chainFunctions(fp.trimNewline, fp.splitByTabs)); 
    
    naiveBayesClassifier = naiveBayesLearner.laplaceSmoothAndReturn();
    return naiveBayesClassifier; 

class DynamicRegionClassifier(object):
    def __init__(self, featureGenerator, trueCategory, categoryToFeatureToProbability):
        self.featureCounts = {};
        self.categoryToFeatureToProbability = categoryToFeatureToProbability;
        allCategories = self.categoryToFeatureToProbability.keys();
        for feature in featureGenerator:
            if feature not in self.featureCounts:
                self.featureCounts[feature] = 0;
            self.featureCounts[feature] += 1;
        if trueCategory not in allCategories:
            raise RuntimeError("category "+trueCategory+" not in list of all categories: "+str(allCategories));
        #assert trueCategory in allCategories;
        self.trueCategory = trueCategory;
        self.categoryLogProbsSoFar = {};
        for category in allCategories:
            self.categoryLogProbsSoFar[category] = 0;

    def predictWithFeature(self,feature):
        """
            Returns what the prediction would be if you include feature
        """
        topCategory = (None, None);
        for category in self.categoryLogProbsSoFar:
            logProb = self.categoryLogProbsSoFar[category] + self.getUpdatedLogProb(category,feature);
            if (topCategory[1] is None or topCategory[1] < logProb):
                topCategory = (category, logProb);
        return topCategory[0];

    def getUpdatedLogProb(self, category, feature):
        if feature in self.featureCounts:
            return self.categoryLogProbsSoFar[category] + self.featureCounts[feature]*math.log(self.categoryToFeatureToProbability[category][feature]); 
        else:
            return self.categoryLogProbsSoFar[category]

    def augmentWithFeature(self, feature):
        for category in self.categoryLogProbsSoFar:
            self.categoryLogProbsSoFar[category] = self.getUpdatedLogProb(category, feature);

def createDynamicRegionClassifiers(theFile,options,naiveBayesClassifier): 
    dynamicRegionClassifiers = [];
    def action(inp, lineNumber): #to be performed on each line of the testing file
        if (lineNumber%options.progressUpdate == 0):
            print "Processed "+str(lineNumber)+" lines of testing file";
        sequence = inp[options.sequenceColIndex].upper();
        category = inp[options.categoryColIndex];
        if 'N' not in sequence:
            dynamicRegionClassifiers.append(DynamicRegionClassifier(kmerGenerator(sequence), category, naiveBayesClassifier.categoryToFeatureToProbability));
    fp.performActionOnEachLineOfFile(fp.getFileHandle(theFile), action=action, ignoreInputTitle=True, transformation=util.chainFunctions(fp.trimNewline, fp.splitByTabs));
    return dynamicRegionClassifiers;

def featureSelectWithNaiveBayes(options, kmerGenerator):
    naiveBayesClassifier = trainNaiveBayes(options, kmerGenerator);
    outputFileHandle = fp.getFileHandle(options.outputFile,'w');
    outputFileHandle.write("no\tfeature\tvalidMisclass\ttestMisclass\n");
    outputFileHandle.flush();
    validation_dynamicRegionClassifiers = createDynamicRegionClassifiers(options.validationFile,options,naiveBayesClassifier);
    testing_dynamicRegionClassifiers = createDynamicRegionClassifiers(options.testingFile,options,naiveBayesClassifier);
    allCategories = naiveBayesClassifier.categoryToFeatureToProbability.keys();
    excludedFeatures = [];
    excludedFeatures.extend(naiveBayesClassifier.categoryToFeatureToProbability[allCategories[0]].keys());
    rankedFeaturesAndMisclassRates = [];
    while len(excludedFeatures) > 0:
        bestFeatureToAddAndMisclassRate = (None, None);
        for i,feature in enumerate(excludedFeatures):
            misclassRateWithFeature = computeFeaturePerf(feature, validation_dynamicRegionClassifiers, options);
            print (i+1),"With",feature,"rate:",misclassRateWithFeature;
            if bestFeatureToAddAndMisclassRate[1] is None or bestFeatureToAddAndMisclassRate[1] > misclassRateWithFeature:
                bestFeatureToAddAndMisclassRate = (feature, misclassRateWithFeature);
        bestFeature = bestFeatureToAddAndMisclassRate[0];
        rankedFeaturesAndMisclassRates.append(bestFeatureToAddAndMisclassRate);
        excludedFeatures.remove(bestFeature);
        testing_misclassRateWithFeature = computeFeaturePerf(feature, testing_dynamicRegionClassifiers, options);
        printString = str(len(rankedFeaturesAndMisclassRates))+"\t"+str(bestFeatureToAddAndMisclassRate[0])+"\t"+str(bestFeatureToAddAndMisclassRate[1])+"\t"+str(testing_misclassRateWithFeature);
        print printString;
        outputFileHandle.write(printString+"\n");
        outputFileHandle.flush();
        for dynamicRegionClassifier in validation_dynamicRegionClassifiers:
            dynamicRegionClassifier.augmentWithFeature(bestFeature);
        for dynamicRegionClassifier in testing_dynamicRegionClassifiers:
            dynamicRegionClassifier.augmentWithFeature(bestFeature);


def computeFeaturePerf(feature, dynamicRegionClassifiers, options):
    misclassificationCount = 0;
    for i,dynamicRegionClassifier in enumerate(dynamicRegionClassifiers):
        predictionWithIncludedFeature = dynamicRegionClassifier.predictWithFeature(feature);
        if predictionWithIncludedFeature != dynamicRegionClassifier.trueCategory:
            misclassificationCount += 1;
    return float(misclassificationCount)/len(dynamicRegionClassifiers);

def classifyWithNaiveBayes(options, kmerGenerator):
    naiveBayesClassifier = trainNaiveBayes(options, kmerGenerator);
    outputFileHandle = fp.getFileHandle(options.outputFile,'w');

    testingFile = fp.getFileHandle(options.testingFile);
    secondaryCategoryToCorrectClassifications = {};
    secondaryCategoryToTotalOccurences = {};
    totalCorrect = util.VariableWrapper(0); #wrappers needed for pass-by-reference to work
    totalTotal = util.VariableWrapper(0);
    def action(inp, lineNumber): #to be performed on each line of the testing file
        sequence = inp[options.sequenceColIndex].upper();
        if ('N' not in sequence):
            if (lineNumber%options.progressUpdate == 0):
                print "Processed "+str(lineNumber)+" lines of testing file";
            category = inp[options.categoryColIndex];
            secondaryCategory = inp[options.secondaryCategoryColIndex];
            if secondaryCategory not in secondaryCategoryToTotalOccurences:
                secondaryCategoryToTotalOccurences[secondaryCategory] = 0;
                secondaryCategoryToCorrectClassifications[secondaryCategory] = 0;
            secondaryCategoryToTotalOccurences[secondaryCategory] += 1;
            totalTotal.var += 1;
            predictedCategory = naiveBayesClassifier.classify(kmerGenerator(sequence));
            if predictedCategory == category:
                secondaryCategoryToCorrectClassifications[secondaryCategory] += 1;
                totalCorrect.var += 1;
    fp.performActionOnEachLineOfFile(testingFile, action=action, ignoreInputTitle=True, transformation=util.chainFunctions(fp.trimNewline, fp.splitByTabs));
    misclassificationRates = [];
    for secondaryCategory in secondaryCategoryToCorrectClassifications:
        correct = secondaryCategoryToCorrectClassifications[secondaryCategory];
        total = secondaryCategoryToTotalOccurences[secondaryCategory];
        misclassificationRates.append({'secondaryCategory': secondaryCategory
            , 'correct': correct
            , 'total': total
            , 'misclassification': (1-float(correct)/total)}); 
    misclassificationRates.append({'secondaryCategory': "overall"
        , 'correct': totalCorrect.var
        , 'total': totalTotal.var
        , 'misclassification': (1-float(totalCorrect.var)/totalTotal.var)});
    misclassificationRates = sorted(misclassificationRates, key=lambda x: -1*x['misclassification']);
    toPrint = [x['secondaryCategory']+": "+str(x['misclassification'])+" ("+str(x['total']-x['correct'])+"/"+str(x['total'])+")" for x in misclassificationRates];
    print "\n".join(toPrint);
    outputFileHandle.write("\n".join(toPrint));

class NaiveBayesLearner(object):
    def __init__(self):
        self.categoryToFeatureToCounts = {};
        self.categoryToTotalFeaturesSeen = {};
        self.categoryToCategoryOccurences = {};
        self.totalExamplesSeen = 0;
        self.allFeaturesSeen = {}; #really a set, I'm using a dictionary cos I'm lazy about looking up syntax
   
    def processInput(self, category, featureGenerator):
        self.totalExamplesSeen += 1;
        if category not in self.categoryToCategoryOccurences:
            self.categoryToCategoryOccurences[category] = 0;
            self.categoryToFeatureToCounts[category] = {};
            self.categoryToTotalFeaturesSeen[category] = 0;
        self.categoryToCategoryOccurences[category] += 1;  
        for feature in featureGenerator:
            self.allFeaturesSeen[feature] = 1;
            if feature not in self.categoryToFeatureToCounts[category]:
                self.categoryToFeatureToCounts[category][feature] = 0;
            self.categoryToFeatureToCounts[category][feature] += 1;
            self.categoryToTotalFeaturesSeen[category] += 1;
 
    def laplaceSmoothAndReturn(self):
        numFeatures = len(self.allFeaturesSeen.keys());
        categoryToFeatureToProbability = {};
        categoryToPriorProbability = {};
        for category in self.categoryToFeatureToCounts:
            categoryToPriorProbability[category] = float(self.categoryToCategoryOccurences[category])/self.totalExamplesSeen;
            categoryToFeatureToProbability[category] = {};
            denominator = self.categoryToTotalFeaturesSeen[category] + numFeatures;
            for feature in self.allFeaturesSeen:
                #initialise with laplace smoothed value
                categoryToFeatureToProbability[category][feature] = float(1)/(denominator);
            for feature in self.categoryToFeatureToCounts[category]:
                #for the features we saw in the training set, compute the laplace smoothed prob:
                numerator = self.categoryToFeatureToCounts[category][feature] + 1;
                categoryToFeatureToProbability[category][feature] = float(numerator)/denominator;
        return NaiveBayesClassifier(categoryToPriorProbability, categoryToFeatureToProbability);

class NaiveBayesClassifier(object):
    def __init__(self, categoryToPriorProbability, categoryToFeatureToProbability):
        self.categoryToPriorProbability = categoryToPriorProbability;
        self.categoryToFeatureToProbability = categoryToFeatureToProbability;   
    def classify(self, featureGenerator):
        categoryToLogProb = {};
        for feature in featureGenerator:
            for category in self.categoryToPriorProbability:
                if category not in categoryToLogProb:
                    categoryToLogProb[category] = math.log(self.categoryToPriorProbability[category]);
                if feature in self.categoryToFeatureToProbability[category]:
                    categoryToLogProb[category] += math.log(self.categoryToFeatureToProbability[category][feature]);
                else:
                    print "Feature "+str(feature)+" did not occur in training set but appears in testing. Ignoring.";
        #find the max
        maxCategory = None;
        maxLogProb = None;
        for category in categoryToLogProb:
            if maxCategory is None or maxLogProb < categoryToLogProb[category]:
                maxCategory = category;
                maxLogProb= categoryToLogProb[category];
        return maxCategory;        


if __name__ == "__main__":
    parser = argparse.ArgumentParser();
    parser.add_argument("--trainingFile",help="Assumes a title is present", required=True);
    parser.add_argument("--validationFile",help="Necessary for the feature selection case");
    parser.add_argument("--testingFile",help="Assumes a title is present", required=True);
    parser.add_argument("--kmerLength", type=int, default=1);
    parser.add_argument("--sequenceColIndex", type=int, default=3);
    parser.add_argument("--categoryColIndex", help="This is the class prediction is attempted for", type=int, default=0);
    parser.add_argument("--secondaryCategoryColIndex", help="This is used in testing stage if you want to partition the error rates by particular categories", type=int, default=2);
    parser.add_argument("--progressUpdate", type=int, default=10000);
    parser.add_argument("--featureSelect", action="store_true");
    parser.add_argument("--outputFile", required=True);
    args = parser.parse_args();
    #don't need any string preprocessing, so pass in identity function as stringPreprocess()
    kmerGenerator = ps.getKmerGenerator(lambda x:x.upper(), args.kmerLength);
    if args.featureSelect:
        util.assertHasAttributes(args,['validationFile'],"Validation file necessary if doing feature selection");
        featureSelectWithNaiveBayes(args, kmerGenerator); 
    else:
        classifyWithNaiveBayes(args, kmerGenerator);
