library(leaps)

args <- commandArgs(trailingOnly = TRUE)

tableIn = read.table(args[1], header=T, sep=",")
pdfOut = args[2]

y = tableIn[,2]
bandValues = tableIn[,3:ncol(tableIn)]

# print('CDOM/DOC values:')
# print(y)
# print('Dimensions of band values:')
# print(dim(bandValues))

nvmax=4
nbest=6
cmax = nvmax*nbest

results <-regsubsets(y~., data=bandValues, nbest=nbest, nvmax=nvmax, really.big = TRUE)

pdf(pdfOut)

coefout <- coef(results, 1:cmax)
plot(results, scale=c('r2'))
summaryresults <- summary(results)

for (i in 1:cmax) {
	print(summaryresults$adjr2[i])
	print(coefout[i])
}





# thecols = 179
# thedata = aa[,1:thecols]
# print(thedata[1,])
# thecols = 183
# they = aa[,thecols:(thecols+1)]
# print(they)

# the.17.24.157 = data.frame(they, thedata)
# print(dim(the.17.24.157))



# thesums = summary(regsubsets(thedata[,1:15], they[,1]))
# print(thesums$adjr2)


# theleaps = summary(leaps(thedata[,1:3], they[,1]))
# print(theleaps)

# summary(lm(they[,1] ~ thedata[,1]))
# summary(lm(they[,1] ~ thedata[,2]))



# colstart = 90
# colend = 98
# thex = thedata[,colstart:colend]
# print(thex[1,])
# they1 = they[,1]
# a<-regsubsets(they1~.,nbest=3,data=thex)
# par(mfrow=c(1,2))
# plot(a,scale="r2")
# par(mfrow=c(1,2))
# plot(a)
# they2 = they[,2]
# b <-regsubsets(they2~.,nbest=3,data=thex)
# plot(b,scale="r2")

# cc = leaps(thex, they1, method = "adjr2")
# print(cc$adjr2)
# print(cc$which)
