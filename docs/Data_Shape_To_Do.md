 jump back into v3 branch - we have new data csv file strucutre -> the file
  now contains all the boxs in the same file -> we will stick to the monthly
  and weekly boxs only -> but the goal is to update the system with the new
  data strcutre -> we will work in iterations -> first i will describe the
  data for you {this data is tagged at new york time zone , the nasdaq market
  is not magnated to the 24 hour system start and end, it have its own cyle ,
  the market opens on 18:00 and closes at 17:00 the next day , so it is 23
  hours open market and from 17 to 18 it closes with zero trade - the data you
  have a a timestamp , this timstamp belongs to the closing day, which means
  the box started the day bofre the time stamp and closed the day of the time
  stamp , the cause for that is that the box have 17 hours of the clsoing day
  and only 6 hours of the opening day, so we have to take that in
  cionsideration when we this data over the candels => example: the box tagged
  5-5-2025 : started at 18:00 4-5-2025 and closed at 17:00 5-5-2025;
  example2: a candele tagged 5-5-2025 22:00 it belongs to the box tagged
  6-5-2025 while a candel tagged 5-5-2025 12:00 belongs to box 5-5-2025} -> do
  deep study on the new box archetecture -> assure the realsult what you have
  undertood with me to confirm it -> documnet it -> read the data the titles
  and sapmle data and dcoumnt the data strcuture -> make sure o account for
  null boxs at pick values ; -> after confiemrig all the new documnttions ->
  move to update the system -> after updating the system luanch the swarm of
  bug bounty team-> genrte bugs report -> update the bug bounty knoledge base
  -> debug the code and solv ebugs -> luanch the hardcode values report
  generatort to grind the codebase -> update the v4 of the report -> fix the
  red issues in the report -> confirm all updates in a new updated ststus
  report -> commit and push -> update thedev brachn with new updates -> switch
  to dev branch and infrom me ; => make sure to confirm vorvbosly with me ;