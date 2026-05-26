this stage is related to the main project
the backtest platform
the backtest now is consist of backend and front end
we can se the backend as the mathamtical engine
that takes a set of paramters
and return the status of this trade(contract(s))
we have established the backtesting system that takes user input and do full backtest and store reults as both logs and stuts summary
now we will implemnt nsga-ii search alogrithm that will play with the paramters do extract the best set of vlue pairs 
the far goal is to take all doachboard paramters control panel vlaues as vector x and get seach for the best vlaues of x that generate the best vlaues of either winrate or total profit 
but for now we will not interduce the whole paramteters as an input
we only will take sl tp as x vlaues to determine the best total progit as y output
but first we have an extra step that is esseintil to coniue
first of all i want the truth table of this system (the backtest platform) that contains all the possible probilities for a trade and the outputs for each
we will etraact that into a md file
then we will compare it to the logic of the subproject-stage1 truth table 
will we find any logiacl contruduction or it is only a simlified verion of the logic 
if we found that it is a siplified verion of the logic 
we will start implemnitng the optimization algortithm nsga-ii or nsga-iii
if we foud an controdcution we have to verify the backtesting logic
cause the subsystem-stage1 is verified by the team leader so it is the more aquarete one
