Add something for table formatting and sometimes the model says more research required in that case it goes ahead and does more research if reequired. It may also ask the user if he wants that and based on the users answer it decides further what needs  to be done


Also configure multihop. IF the agent feels in that the context it got is not sufficeint after reading all teh chunnks or maybe some chunks redirect to other things then another searches should be allowed. This should have a check that at max N number of hops are allowed. Rather than now streaming the answer we need to post process it each time and see if we need to get more results or not.

A Simple Example
Single-hop question: "Who directed the movie Oppenheimer?"
(The agent searches this once, finds "Christopher Nolan," and answers).

Multi-hop question: "Who is the wife of the director of the movie Oppenheimer?"
(The agent must first search for the director of Oppenheimer -> finds Christopher Nolan. Then it must take that new information and do a second search for Christopher Nolan's wife -> finds Emma Thomas).




How is the evaluation being done ???


shoudl the re-research not be a button ???


how many next re-research steps ??