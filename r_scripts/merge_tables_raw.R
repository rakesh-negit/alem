args <- commandArgs(trailingOnly = TRUE)

table1 = read.table(args[2], header=T, sep=',')

for (filename in args[0:-2]){
	table2 = read.table(filename, header=T, sep=',')
	table1 = merge(table1, table2, by = "NID")
}

write.table(table1, args[1], quote = F, row.names = F, sep=',')



