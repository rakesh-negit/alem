args <- commandArgs(trailingOnly = TRUE)
						 
 
regressionTableFilename <- args[1]
txtOutput <- args[2]
csvModelOutput <- args[3]
pdfOutput <- args[4]

regressionTable = read.table(regressionTableFilename, header=T, sep=",")
						 
regressionNIDs = regressionTable[[1]]
regressionCDOM = regressionTable[[2]]
regressionBands = regressionTable[[3]]
			 
thelakedata = data.frame(regressionNIDs,regressionCDOM,regressionBands)

print(summary(thelakedata))
print(thelakedata)

##################



## functions adapted from 
#Rcode-glminlakeswithprediction-8
###################################

afn.plotregression.with.intervals = function(theindependent, thedependent,thelinearmodel,theadd=F,thexlab = "",addhistograms=F,sleeptime=0)
# works for one independent, one dependent.
  {

 
  # draws the red and green interval bars
  xRange=data.frame(logthexvalue=seq(min(theindependent,na.rm=T), max(theindependent,na.rm=T),0.01))
  #xRange=data.frame(logthexvalue=seq(0.5, 1.8,0.01))
  #print(xRange)
  print("predicting for drawing the interval bars")
  theret = afn.singlemodel.predict.withpredictionintervals(thelinearmodel, xRange)
  print(dim(theret))
  thepred = theret[,1]
  thesefit = theret[,2]
  print("making the plot")
  pred4plot = data.frame(thepred
                         ,(thepred-thesefit), (thepred+thesefit)
  )
  # End of: draws the red and green interval bars
  
  # add histograms on x axis
  # note that truehist is difficult to implement because of the call to 'top'. the calls to hist work just fine.
  def.par <- par(no.readonly = TRUE) # save default, for resetting...
  
  #here
  if(addhistograms)
  {
    x = theindependent
    y = thedependent
    #x <- pmin(3, pmax(-3, rnorm(50)))
    #y <- pmin(3, pmax(-3, rnorm(50)))
    xhist <- hist(x, breaks=seq(0.8,1.8,0.05), plot=FALSE)
    yhist <- hist(y, breaks=seq(0,25,0.5), plot=FALSE)
    top <- max(c(xhist$counts, yhist$counts))
    xrange <- c(0.8,1.8)
    yrange <- c(0,25)
    nf <- layout(matrix(c(2,0,1,3),2,2,byrow=TRUE), c(3,1), c(1,3), TRUE)
    #layout.show(nf)
    
    par(mar=c(3,3,1,1))
  }
  ## Plot lines derived from best fit line and confidence band datapoints
  
  matplot(
    xRange,
    pred4plot, 
    lty=c(1,2,2),   #vector of line types and widths
    type="l",       #type of plot for each column of y
    #xlim=c(0.8,1.8),
    ylim=c(0,12),
    xlab = thexlab,
    ylab="",
    add=theadd
  )
  legend("topright", bty="n", legend=paste("R2 is ", format(summary(thelinearmodel)$r.squared, digits=4)))
  
  points(theindependent, thedependent)
  
  if(addhistograms)
  {
    #plot(x, y, xlim=xrange, ylim=yrange, xlab="", ylab="")
    par(mar=c(0,3,1,1))
    barplot(xhist$counts, axes=FALSE, ylim=c(0, top), space=0)
    par(mar=c(3,0,1,1))
    barplot(yhist$counts, axes=FALSE, xlim=c(0, top), space=0, horiz=TRUE)
    
    par(def.par)
  }
}

#######


afn.singlemodel.getmodel.log = function(thexvalue, theyvalue, theweights = rep(1, length(thexvalue)))
  
{
  # first, we will prune out any nodata values.
  thexy = data.frame(thexvalue, theyvalue)
  print(dim(thexy))
  thexy = thexy[!is.na(thexy$thexvalue),]
  thexy = thexy[!is.na(thexy$theyvalue),]
  print(dim(thexy))
  thexvalue = thexy$thexvalue
  theyvalue = thexy$theyvalue
  
  logthexvalue = log(thexvalue)
  #	logthexvalue.model = logthexvalue # for later use
  # i need the x value in the later 'predict' call to be named logthexvalue, same as what was used to create the model. so here I save the model x value for later plotting.
  #rm(theglmmodel)
  
  # first let us record the lm in log space for the r2.
  print("the model in log-log space is:")
  linear.log.log.model=lm(log(theyvalue)~ logthexvalue)
  print(summary(linear.log.log.model))
  print("returning the linear log-log model")
  return(linear.log.log.model)
  # what is up with the slope and interecept being unexpected?  but the r2 is what jb has, so it seems ok.

  # here I deleted a whole bunch of this stuff out.
#  theglmmodel=glm(theyvalue~ logthexvalue,family=Gamma(link=log), weights = theweights)
  # for a gamma function
  
#  print ("the relation between x and log(y) is")
#  print(theglmmodel)
#  theglmmodel.response.fit = predict(theglmmodel,type="response")
  #	plot(theglmmodel.response.fit)
#  theglmmodel.response.residuals = residuals(theglmmodel,type="response")
#   print("observed residuals in real space:")
#   print(data.frame(thexvalue, theyvalue, theglmmodel.response.fit, theglmmodel.response.residuals))
#   sqresids = theglmmodel.response.residuals * theglmmodel.response.residuals
  #    print(sqresids)
#   thermse = sum(sqresids)/length(sqresids)
#   print("the root mean squared error of the predicted values in real space:")
#   print(paste("RMSE is", thermse))
#   #	plot(theglmmodel.response.residuals)
#   #	plot(theglmmodel.response.fit, theglmmodel.response.residuals)
#   
#   return(theglmmodel)
}


afn.singlemodel.predict.withpredictionintervals = function(themodel, thexvalue)
{
  logthexvalue = log(thexvalue)
  
  # for now, I will test it using the lakes used to make the regression
  #rm(cc)
  # note: changed from predict.glm to predict. 
  cc2 = predict(themodel,newdata = data.frame(logthexvalue), se.fit=T,type="response")
  thepred = cc2$fit 
  thepred.responseunits = exp(thepred)
  thestd.err.fit = exp(cc2$se.fit)
  predictioninterval = thestd.err.fit * 1.96
  #  following , it should be
  ##  https://stat.ethz.ch/pipermail/r-help/2010-September/254465.html
  #  thesefitinresponseunits = exp(cc2$se.fit)*1.96

  theret = data.frame(thepred.responseunits, thestd.err.fit, predictioninterval)
  return(theret)
}



## get a subset of samples. quebec. trimming only the very highest single value, which is suspicious. the 
# older versions of this file have a function called afn.dobigfunction, and they can be run to be compared to this. there is test code there. etc.

# now try to incorporate the two together.
# may 2013

theindependent = regressionBands
thedependent = regressionCDOM
chosenmodel = afn.singlemodel.getmodel.log(theindependent, thedependent)
print(summary(chosenmodel))
rsquared = summary(chosenmodel)$r.squared
save(chosenmodel, file=txtOutput,ascii=T)

# do a prediction on the set the model was built on.
theret = afn.singlemodel.predict.withpredictionintervals(chosenmodel, theindependent)
thepred = theret[,1]
these.fit = theret[,2]
predictioninterval.ithink = theret[,3] # note we had multiplied the se.fit by exp(se.fit)*1.96
groundcarbonvalue = thedependent
imageryvalue = theindependent
predictions.forfusion = (data.frame(regressionNIDs, imageryvalue, groundcarbonvalue, thepred, these.fit, predictioninterval.ithink))
write.table(predictions.forfusion, csvModelOutput, row.names= F, quote = F, sep=",")

# save a plot of the model with the data it built.
pdf(pdfOutput)
  afn.plotregression.with.intervals(theindependent, thedependent,chosenmodel, theadd=F
                                    ,addhistograms=F)
  # title doesn't seem to work bc of the specialized plot funct with histograms that we use.
  #title(main="main title", sub="sub-title", xlab="x-axis label", ylab="y-axis label")
dev.off()

# do a prediction on the larger prediction set.
# read in the prediction data. Access the right ratio(s).
# set theindependent to be the X values of all of them.
# set NIDs for the predicted ones too.



