
# script for assessing the quality of a run and to do a bunch of stuff

tinyamount <- 0.001

afn.computestandarderror <- function(thelist)
	{
	return(sqrt(var(thelist))/ sqrt(length(thelist)))
	}	


afn.sumacrosscols <- function(theinputtable)
	{
	# calculate marginal totals for rows and columns simultaneously
	sumacrosscols <- rep(0, dim(theinputtable)[1])
	for(j in 1:dim(theinputtable)[2])
			{
			sumacrosscols<- sumacrosscols + theinputtable[,j]

			}				
	return(sumacrosscols)
	}

afn.calculatekappa <- function(inputtable)
	{
	# first, figure out the dimensionality of the table
	dimen <- sqrt(length(inputtable))

	# can automatically sum over the whole table to get the number
	# of cases.
	n <- sum(inputtable)

	# agresti uses probabilities, so convert the occurrence table to a 
	# probability table
	thetable <- inputtable/n

	# make data structure for rows and column marginal probabilities
	rowmargprob <- rep(0, dimen)
	colmargprob <- rep(0, dimen)

	# calculate marginal totals for rows and columns simultaneously
	for(i in 1:dimen)
		for (j in 1:dimen)
			{
			rowmargprob[i] <- rowmargprob[i] + thetable[i,j]
			colmargprob[i] <- colmargprob[i] + thetable[j,i]
			}				

	# calculate kappa
	diagsum <- 0
	kappasecterm <- 0
	for(i in 1:dimen)
		{
		diagsum <- diagsum + thetable[i,i]
		kappasecterm <- kappasecterm + (rowmargprob[i] * colmargprob[i])
		}
	khat <- (diagsum - kappasecterm) / (1-kappasecterm)


	#calculate stddevofkhat
	pzero <- diagsum
	pe <- kappasecterm

#	print(paste(pzero,pe))

	# get the summation term in the second overall term for var(khat)
	suminsecond <- 0
	for(i in 1:dimen)
		{
		suminsecond <- suminsecond + 
				thetable[i,i] * (rowmargprob[i] + colmargprob[i])
		}
	# get the summation term in the second overall term for var(khat)
	doublesuminthird <- 0
	for(i in 1:dimen)
		for(j in 1:dimen)
			{
			doublesuminthird <- doublesuminthird +
				thetable[i,j] * (rowmargprob[j] * colmargprob[i])
			}



	#checked very closely green p. 159-160
	# note the typo in congalton.  Noticed it in Agresti p. 367.
	# typo is that it's one minus theta2, squared, in the denominator
	# of the first term.  



	first <- ((pzero * (1-pzero)) / ((1-pe)**2))
	second <- (2*(1-pzero) * ( 2 * pzero * pe - 
				suminsecond)
			/
		((1-pe)**3))
	third <- ((
		((1 - pzero)**2) * doublesuminthird)
		/
		((1-pe)**4))

#	print(first)
#	print(second)
#	print(third)
		
	varkhat <- (first + second + third) / n
	stdevkhat <- sqrt(varkhat)

	return(list(khat=khat,stdevkhat=stdevkhat))
	}

# afn.calculatetaus <- function(inputtable)
	# {
	# return(afn.calculatetaue(inputtable), 
		# afn.calculatetaup(inputtable))
	# }

afn.calculatetaue <- function(inputtable)
	# this function calculates taue.  It assumes equal
	# a priori probablities for each class.
	{
	# 
	# first, figure out the dimensionality of the table
	dimen <- sqrt(length(inputtable))

	# can automatically sum over the whole table to get the number
	# of cases.
	n <- sum(inputtable)

	# agresti uses probabilities, so convert the occurrence table to a 
	# probability table
	thetable <- inputtable/n

	# make data structure for rows and column marginal probabilities
	rowmargprob <- rep(0, dimen)
	colmargprob <- rep(0, dimen)

	# calculate marginal totals for rows and columns simultaneously
	for(i in 1:dimen)
		for (j in 1:dimen)
			{
			rowmargprob[i] <- rowmargprob[i] + thetable[i,j]
			colmargprob[i] <- colmargprob[i] + thetable[j,i]
			}				

	# calculate taue
	diagsum <- 0

	for(i in 1:dimen)
		{
		diagsum <- diagsum + thetable[i,i]

		}

	pr <- 1/dimen

	taue <- (diagsum - pr) / (1-pr)


	#calculate stddevoftaue
	pzero <- diagsum

	vartaue <- ((pzero * (1 - pzero)) / 
				( n * ((1-pr)**2)))

#	print(paste("vartaue",vartaue))
	stdevtaue <- sqrt(vartaue)

	return(list(taue=taue, stdevtaue=stdevtaue))
	}


afn.calculatetaup <- function(inputtable)
	# this function calculates taup.  It uses the marginal reference
	# data probabilities
	# as the a priori probabilities.  Note that it assumes very strongly
	# that the COLUMN marginal probablities are for the reference
	# data.
	#
	{
	# 

	# first, figure out the dimensionality of the table
	dimen <- sqrt(length(inputtable))

	# can automatically sum over the whole table to get the number
	# of cases.
	n <- sum(inputtable)

	# agresti uses probabilities, so convert the occurrence table to a 
	# probability table
	thetable <- inputtable/n

	# make data structure for rows and column marginal probabilities
	rowmargprob <- rep(0, dimen)
	colmargprob <- rep(0, dimen)

	# calculate marginal totals for rows and columns simultaneously
	for(i in 1:dimen)
		for (j in 1:dimen)
			{
			rowmargprob[i] <- rowmargprob[i] + thetable[i,j]
			colmargprob[i] <- colmargprob[i] + thetable[j,i]
			}				

	# calculate taup
	diagsum <- 0
	pr <- 0
	for(i in 1:dimen)
		{
		diagsum <- diagsum + thetable[i,i]
		pr <- pr + (colmargprob[i] ** 2)
		}
	taup <- (diagsum - pr) / (1-pr)

#	print(paste("pr for taup",pr))
	#calculate stddevoftaup
	pzero <- diagsum

	vartaup <- ((pzero * (1 - pzero)) / 
				( n * ((1-pr)**2)))

#	print(paste("var for taup",vartaup))

	stdevtaup <- sqrt(vartaup)

	return(list(taup=taup, stdevtaup=stdevtaup))
	}

