source("r_scripts\\select_training_set.R")
source("r_scripts\\afn.kappa-tau-taup-taue.R")

library(rpart)

args <- commandArgs(trailingOnly = TRUE)

treeBuildData = read.table(args[1], sep=",", header=T)
treeBuildPdfOut = args[2]
treePredictionCsvOut = args[3]

## Split into testing and training
# splitBuildData = afn.selecttrainingset(treeBuildData , 50)
# trainingData = splitBuildData[[1]][2:dim(splitBuildData[[1]])[2]]
# testingData = splitBuildData[[1]][2:dim(splitBuildData[[2]])[2]]
# tableOut <- treeBuildData[splitBuildData[[4]],c(1,2)]

# Use only B5DIVB8
# newTreeBuildData = treeBuildData[,c(1,2)]
# newTreeBuildData$B5DIVB8 <- treeBuildData$B5DIVB8
# treeBuildData = newTreeBuildData


# Don't split
trainingData = treeBuildData[2:dim(treeBuildData)[2]]
testingData = treeBuildData[2:dim(treeBuildData)[2]]
tableOut <- treeBuildData[,c(1,2)]

hilothreshold = 1.5
traininghilo = trainingData$CDOM > hilothreshold
traininghilo = as.factor(traininghilo)

testinghilo = testingData$CDOM > hilothreshold
testinghilo = as.factor(testinghilo)

trainingData = data.frame(trainingData, traininghilo)
testingData = data.frame(testingData, testinghilo)

trainingData$CDOM <- NULL
testingData$CDOM <- NULL

print(testingData[1,])
print(trainingData[1,])


# print(summary(trainingData))
# print(dim(trainingData))
# print(trainingData)
# print(sort(trainingData$CDOM))

controlSettings <- rpart.control(cp=0.01, maxdepth=20)

#tree.CDOM <- rpart(CDOM~., trainingData, method='class')#, control=controlSettings)
#tree.CDOM <- rpart(traininghilo~., trainingData, method='class')#, control=controlSettings)
#tree.CDOM <- rpart(traininghilo~B3DIVB8+B4DIVB8, trainingData, method='class')#, control=controlSettings)
tree.CDOM <- rpart(traininghilo~., trainingData, method='class')#, control=controlSettings)
#tree.CDOM <- rpart(CDOM~., trainingData)

pdf(treeBuildPdfOut)
plot(tree.CDOM)
text(tree.CDOM)

testingPredicted = predict(tree.CDOM, newdata=testingData, type='class')
print(length(testingPredicted))
tableOut$CDOM_PRED <- testingPredicted
write.table(tableOut, treePredictionCsvOut, quote = F, row.names = F, sep=',')

kappaTauFn = args[4]
print(dim(testingPredicted))
print(testingData$CDOM)



ktTable = table(testingPredicted, testinghilo)

print(ktTable)
print(summary(ktTable))
print(dim(ktTable))

capture.output(afn.calculatetaue(ktTable), file=kappaTauFn)
capture.output(afn.calculatetaup(ktTable), file=kappaTauFn, append=TRUE)
capture.output(afn.calculatekappa(ktTable), file=kappaTauFn, append=TRUE)

#Do it with B5DIVB8 only

dev.off()