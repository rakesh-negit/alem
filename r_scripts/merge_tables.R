args <- commandArgs(trailingOnly = TRUE)

table1 = read.table(args[2], header=T, sep=',')

for (filename in args[0:-2]){
	table2 = read.table(filename, header=T, sep=',')
	table1 = merge(table1, table2, by = "NID")
}

table1$Rowid_ <- NULL
table1$ZONE_CODE <-NULL
table1$STD <- NULL
table1$SUM <- NULL
table1$RANGE <- NULL
table1$COUNT <- NULL
table1$MAX <- NULL
table1$MEAN <- NULL
table1$MIN <- NULL
table1$AREA <- NULL

write.table(table1, args[1], quote = F, row.names = F, sep=',')



