args <- commandArgs(trailingOnly = TRUE)

csvIn = args[1]
csvOut = args[2]

tableIn = read.table(csvIn, sep=',', header=T)

tableIn$CHL = NULL
tableIn$COUNT_CDOM = NULL
tableIn$SCENE_ID = NULL
tableIn$B1_MIN = NULL
tableIn$B2_MIN = NULL
tableIn$B3_MIN = NULL
tableIn$B4_MIN = NULL
tableIn$B5_MIN = NULL
tableIn$B6_MIN = NULL
tableIn$B7_MIN = NULL
tableIn$B8_MIN = NULL

write.table(tableIn, csvOut, quote = F, row.names = F, sep=',')