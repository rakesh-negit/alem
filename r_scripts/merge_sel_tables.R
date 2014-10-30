args <- commandArgs(trailingOnly = TRUE)

table1 = read.table(args[2], header=T, sep=',')
table2 = read.table(args[3], header=T, sep=',')

table2$CDOM <- NULL
table2$COUNT <- NULL
table2$COUNT_CDOM <-NULL
	
tableOut = merge(table1, table2, by = "CJRS_LAKE")

write.table(tableOut, args[1], quote = F, row.names = F, sep=',')