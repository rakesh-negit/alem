args <- commandArgs(trailingOnly = TRUE)

table1 = read.table(args[2], header=T, sep=',')
table2 = read.table(args[3], header=T, sep=',')

table1$ZONE_CODE <- NULL
table1$STD <- NULL
table1$SUM <- NULL
table1$RANGE <- NULL
table1$COUNT <- NULL
table1$MAX <- NULL
table1$MEAN <- NULL
table1$MIN <- NULL
table1$AREA <- NULL

table2$ZONE_CODE <- NULL
table2$STD <- NULL
table2$RANGE <- NULL
table2$COUNT <- NULL
table2$MAX <- NULL
table2$MEAN <- NULL
table2$MIN <- NULL
table2$AREA <- NULL

tableOut = merge(table1, table2, by = 'NID')

write.table(tableOut, args[1], quote = F, row.names = F, sep=',')



