#!/usr/bin/env python
import sys, os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import fileProcessing as fp;
import util;

def select(options):
   
    transformation = util.chainFunctions(fp.trimNewline, fp.splitByTabs);
    print options.inputFiles;
    for inputFile in options.inputFiles:
        outputFile = options.outputFile;
        print outputFile
        if (options.outputFile is None):
            prefix = util.addArguments("selected",[util.ArrArgument(options.colsToSelect,"cols")
                                                    ,util.CoreFileNameArgument(options.fileWithColumnsToSelect,"colNames")]
                                        );
            outputFile = fp.getFileNameParts(inputFile).getFilePathWithTransformation(lambda x: prefix+"_"+x); 
            print outputFile;
        outputFileHandle = fp.getFileHandle(outputFile, 'w');
        
        def actionFromTitle(title):
            titleArr = transformation(title);
            #if columns are listed in fileWithColumnsToSelect, append to colsToSelect
            colsToSelect = [x for x in options.colsToSelect];
            if (options.fileWithColumnsToSelect is not None):
                colNameToIndex = util.valToIndexMap(titleArr);
                colNames = fp.readRowsIntoArr(fp.getFileHandle(options.fileWithColumnsToSelect));
                for colName in colNames:
                    if colName not in colNameToIndex:
                        raise ValueError("Column "+str(colName)+" is not in title");
                colNameIndices = [colNameToIndex[x] for x in colNames];
                colsToSelect.extend(colNameIndices);
            
            def action(inp, lineNumber):
                arrToPrint = [inp[x] for x in colsToSelect];
                outputFileHandle.write("\t".join(arrToPrint)+"\n");
            action(titleArr, 0); #print out the first line; even if there's no title, this still works.
            return action;
        fp.performActionOnEachLineOfFile(
            fileHandle=fp.getFileHandle(inputFile)
            ,transformation=transformation
            ,actionFromTitle=actionFromTitle
            ,ignoreInputTitle=True #this isn't problematic because I call 'action' on the first line no matter what
            ,progressUpdate=options.progressUpdate
        );        
        outputFileHandle.close();

if __name__ == "__main__":
    parser = argparse.ArgumentParser();
    parser.add_argument("--inputFiles", nargs='+', required=True);
    parser.add_argument("--outputFile");
    parser.add_argument("--colsToSelect", type=int, nargs='+', default=[]);
    parser.add_argument("--fileWithColumnsToSelect");
    parser.add_argument("--progressUpdate", type=int, default=10000);   
    args = parser.parse_args();
 
    if (args.outputFile is not None):
        if (len(args.inputFiles) > 1):
            raise ValueError("If more than 1 input file is specified, outputFile names will be autogenerated - do not specify");

    select(args);  
