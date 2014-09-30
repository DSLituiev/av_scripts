#!/usr/bin/python
import sys;
import gzip;
import fileProcessing as fp;
sys.path.insert(0,"./parallelProcessing");
import parallelProcessing as pp;
import parallelisingFunction as pf;
import os;

if (len(sys.argv) < 3):
	print "arguments: [inputBedFile] [outputFile]";
	sys.exit(1);

inputBedFile = sys.argv[1];
finalOutputFile = sys.argv[2];
pathToFaFromChrom = lambda chrom : "/home/avanti/Enhancer_Prediction/EncodeHg19MaleMirror/"+chrom+".fa";

bedToFasta(inputBedFile, finalOutputFile, pathToFaFromChrom);

def bedToFasta(inputBedFile, finalOutputFile, pathToFaFromChrom):

	tempOutputDir = os.environ['TMP'];
	if (tempOutputDir == ""):
		print "Please set the TMP environment variable to the temp output directory!";
		raise;

	filePathMinusExtensionFromChromosome = lambda chrom: tempOutputDir + "/" + chrom+"_"+getFileNameParts(inputBedFile).coreFileName;
	bedFilePathFromChromosome = lambda chrom: filePathMinusExtensionFromChromosome(chrom)+".bed"; 
	fastaFilePathFromChromosome = lambda chrom: filePathMinusExtensionFromChromosome(chrom)+".fasta";

	def bedtoolsCommandFromChromosome(chrom):
		return "bedtools getFasta -tab -fi "+pathToFaFromChrom(chrom)+" -bed "+bedFilePathFromChromosome(chrom)+ " -fo "+fastaFilePathFromChromosome(chrom);
	
	#step 1: split lines into other files based on 'filter variables' extracted from each line.
	chromosomes = fp.splitLinesIntoOtherFiles(
		fp.getFileHandle(inputBedFile) #the file handle that is the source of the lines
		, fp.splitByTabs #preprocessing step to be performed on each line
		, fp.lamdbaMaker_getAtPosition(0) #filter variable from preprocessed line
		, bedFilePathFromChromosome #function to produce output file path from filter variable
	);

	parallelisingFactory = pp.ParallelisingFactory(pp.ParalleliserInfo( #wrapper class - put in place for possible future extensibility.
								pf.ThreadBasedParalleliser(
									#function to execute on each input, in this case each chromosome
									lambdaProducer_executeAsSystemCall(bedtoolsCommandFromChromosome)
								))).getParalleliser(chromosomes).execute();

	fp.concatenateFiles(finalOutputFile, [fastaFilePathFromChromosome(chrom) for chrom in chromosomes]);
	 
