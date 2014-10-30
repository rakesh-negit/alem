args <- commandArgs(trailingOnly = TRUE)

table1 = read.table(args[1], header=T, sep=',')

tempColumn <- table1$COUNT_CDOM
table1$COUNT_CDOM <- NULL
#table1 <- append(table1, tempColumn)
table1$COUNT_CDOM <- tempColumn 

write.table(table1, args[1], quote = F, row.names = F, sep=',')