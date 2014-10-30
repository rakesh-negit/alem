## functions for training and testing. more recent ones are at top.

afn.selecttrainingset <- function (dataframe, percent, tsetname = "training1.txt", rsetname = "remaining1.txt"
)
  # Writes a pair of dataframes for training set and for the remainder set of data
  # from the data frame "dataframe".  Percent represents the proportion
  # of the data to put in the training set.  100 - percent of the data
  # will be put in the remainder set.
  
{
  print("in afn.selecttrainingset")
  fullsetlength <- dim(dataframe)[[1]]
  
  temprowsinset <- afn.pickrowsfortraining(fullsetlength, percent)
  print(temprowsinset)
  # now we can proceed with the iteration.   
  
  
  dftset <- {}
  dfrset <- {}
  testingrows = {}
  tsetcounter <- 1
  for (i in 1:fullsetlength)
  {
    if(i%%20 == 0) print(i)
      if(temprowsinset[tsetcounter] == i)
        {
          print(paste("row",i,"is training."))
          dftset=rbind(dftset, dataframe[i,])
          #    advance to wait for next training set element.
          if(tsetcounter < length(temprowsinset))  # but don't iterate past the end of the set of training rows.
            {        
            tsetcounter <- tsetcounter + 1
            print(paste("next item in training list is item number",tsetcounter))
            }
            else
            {tsetcounter=1 ## set it back to an early row, which won't be matched again. prevents falling off end of the temprowsinset array
            }

        }
    else
    {
      print(paste("row",i,"is testing."))
      testingrows = c(testingrows,i)
      dfrset=rbind(dfrset, dataframe[i,])
    }
  }
 # print(dftset)
#  print(dfrset)
  return(list(dftset, dfrset, temprowsinset, testingrows))
}




afn.writeappend.matrix <- function(x, thefile = "", thesep = " ")
{
  #       x<- as.matrix(x)
  #      p <- ncol(x)
  #     cat(format(t(x)), file = file, append = T, fill = T, width = 10,
  #            sep = c(rep(sep,p-1),"\n"))
  write.table(x,file=thefile,sep=thesep, append = T, col.names = F, row.names = F)  
}




afn.selecttrainingset.v3 <- function (dataframe, percent)
  # Writes a pair of files for training set and for the remainder set of data
  # from the data frame "dataframe".  Percent represents the proportion
  # of the data to put in the training set.  100 - percent of the data
  # will be put in the remainder set.  
  
{
  fullsetlength <- dim(dataframe)[[1]]
  
  rowsinset <- afn.pickrowsfortraining(fullsetlength, percent)
  
  tsetname <- "training1.txt"
  rsetname <- "remaining1.txt"
  afn.writeheader.matrix(dataframe, tsetname, ", ")
  afn.writeheader.matrix(dataframe, rsetname, ", ")
  tsetcounter <- 1
  for (i in 1:fullsetlength)
  {
    if(i%%20 == 0) print(i)
    if(rowsinset[tsetcounter] == i)
    {
      afn.writeappend.matrix(dataframe[i,], tsetname, ", ")
      #		advance to wait for next training set element.
      tsetcounter <- tsetcounter + 1
    }
    else
    {
      afn.writeappend.matrix(dataframe[i,], rsetname, ", ")
    }
  }
}



####### less recent ones are below.

afn.write.matrix <- function(x, file = "", sep = " ")
{
	x<- as.matrix(x)
	p <- ncol(x)
	cat(dimnames(x)[[2]],format(t(x)), file = file,
		sep = c(rep(sep,p-1),"\n"))

}


afn.writeappendold.matrix <- function(x, file = "", sep = " ")
{
        x<- as.matrix(x)
        p <- ncol(x)
        cat(format(t(x)), file = file, append = T, fill = 10,
                sep = c(rep(sep,p-1),"\n"))
 
}
 
afn.writeheaderold.matrix <- function(x, file = "", sep = " ")
{
        x<- as.matrix(x)
        p <- ncol(x)
        cat(dimnames(x)[[2]], file = file, 
                sep = c(rep(sep,p-1),"\n"))
 
}
 
afn.readadataframe <- function(newframename, thefile = "", thesep = " ")
{
	read.table(file = thefile,T,sep=thesep,row.names = NULL)

}

afn.readadataframeorig <- function(newframename, thefile = "", thesep = " ")
{
        read.table(file = thefile,T,sep=thesep)
 
}
 

 
afn.writeheader.matrix <- function(x, file = "", sep = " ")
{
        x<- as.matrix(x)
        p <- ncol(x)
        cat(dimnames(x)[[2]], file = file,
                sep = c(rep(sep,p-1),"\n"))
 
}
 
afn.pickrowsfortraining <- function (fullsize,percent)
# returns a vector of row numbers from the vector 1:fullsize
# The values are selected randomly from the vector 1:fullsize
{
	subsetlength <- trunc(fullsize * percent / 100)
	print(subsetlength)

	tempvec <- 1:fullsize
	resultvecalmost <- sample(tempvec, subsetlength)
	resultvec <- sort(resultvecalmost)	
	print(resultvec)
  print("returning from picking rows for training. Immediately above was the rows picked.")
  print(paste("picked", length(resultvec),"out of",(fullsize)))
	return(resultvec)
}


afn.selecttrainingset.oldie <- function (dataframe, percent)
# Writes a pair of dataframes for training set and for the remainder set of data
# from the data frame "dataframe".  Percent represents the proportion
# of the data to put in the training set.  100 - percent of the data
# will be put in the remainder set.
 
{
  fullsetlength <- length(dataframe[,1])
 
  temprowsinset <- afn.pickrowsfortraining(fullsetlength, percent)

# hack:  if the length of rowsinset was equal to the length of the 
# list of numbers to subset, I would need a test, encountered throughout
# the loop at each iteration, to make sure that I didn't go beyond the
# last element of the training set list.  I can avoid that test if I 
# make a list that's one item longer, and just put a value in that 
# last item that won't match with the row counter.  In this case that item 
# will be zero.

# now we can proceed with the iteration.   


  dftset <- {}
  dfrset <- {}
  tsetcounter <- 1
  for (i in 1:fullsetlength)
  {
    if(i%%20 == 0) print(i)
    if(temprowsinset[tsetcounter] == i)
    {
      rbind(dftset, dataframe[i,])
      print(dftset)
      #  	advance to wait for next training set element.
      tsetcounter <- tsetcounter + 1
    }
    else
    {
      rbind(dfrset, dataframe[i,])
      print(dfrset)
      
    }
  }

  return(list(dftset, dfrset))
}
 

