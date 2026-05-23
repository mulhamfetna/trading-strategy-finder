 
 for the following focus and brainstroml you have to study it ; then summerie it; then confirm the
  facts with me ; then documetning them; then after confiming it will be transformed into action plan
  and todo list ; after that you will satrt tackling with the code base to fit the new startegy; now we
  will start backtesting using tradeview own startegy insteade of your startegy ; so first of all you
  will apnden your own currunt startegy and intrerducte the code to the tradveiw own startegy; usnig the
  same paramteres but the decision making process will be affected ; first of all lets interduce boxs;
  tradview have boxs system; you have now two boxs files; the 'NQ_week_data.csv' & 'NQ_month_data.csv' ;
  the coding system is the follwing ; the date is the starting date of the box "BUT IT NEED PRE
  PROCCING WHICH WE WILL DO AFTER YOU UNDERSTAND THE STARTEGY" the weekly box is a box that have two
  values the upper value and the lower vlaue coded as the fourth charachter of the columns ---U & ---D;
  so that generates a swuare that vertically start from the date and stops after one month or one week
  according to the data table the first character stands for month or week M--- & W---; the staregy says
  if the price is going up and it went above the upper edge of the box this is an action , if the price
  going down and it goes under the down edge it is an action , if the price bouncing inside the box
  which means it entered the box but never made it all the way through it to the other side this is
  holding with no action taken; the reason we have multiple boxs that as the price going up it bassed
  the first box down and up ednge so it considered an action a new higher value box will open so it
  either also coninue to bass through the new one and considered a new action or not so it is hold or
  stay below it so it is concidered action also; by actions we means long and short; if it passed the
  donw and up edge that tells us that it is still going higehr and that tells us to buy more if it
  passed the upper and dwon edge it tells us that the proce is still going down and we should sell more
  ; as i mentioned accrding to the price a new higher value boxs open ; so we have to expect on the
  edges of the range messing boxs when the price never reached the far up or that far down ; so alwwasy
  we have to cekcck for null values ; we have covered the first cahrater and the fourth charachters of
  the cumns naminf ; the middle two characters is garpeg just fancy naming system ; this is the naming
  system {[Pasted text #1 +35 lines]} ; now we are not counting for the intersected bos we are checing
  for indivual boxs for action ; the intersected bos is for later iteration; make sure the monthly boxs
  apply for all the month candles and the weekly box applys for the weekly box data; IMPORTNAT TOP
  PRTIOTY ACTION: shift the boxs by -2 FOR ONLY ONE TIME IN SPERTED SCIPT AND SAVE THE UPDATED TABLES;
  so the date you have in the box data is teh starting dat and you add up to 30 days r 7 days whether a
  week or moth; the mopen is the opingn price of the month and wopen is
     the opnin gprice of the week
-> see the two intersected boxs rule; abanden it for now; we are checking only one box at the time
  logic ; as soon we make it to other side of one of the boxs we will take action; the boxs is still not
  drawn in the graph; 