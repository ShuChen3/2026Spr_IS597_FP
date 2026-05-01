# 2026Spr_projects - Rummikub Endgame Puzzle Generator and Solver
In this project I tried to build a game environment for creating a rummikub end game
puzzle for player to solve.


Instead of using only the standard Rummikub rules, I added two original types of special 
tiles to make the game more challenging and interesting. The first one is the **Rainbow King**, 
which can be used in a run to connect tiles with different colors and fill the missing middle value. 
The second one is the **Prism Joker**, which can replace any value tile of one fixed color.

The current generator and solver both have high computational complexity, because the problem itself 
is a combinatorial search problem. The program uses graph-based candidate generation and backtracking-based 
solving, so the worst-case time complexity can still be exponential.


# Future improvment
1.Enable players to customize more game rules through parameters, such as the number of tile colors, 
the range of tile values, and special tile rules.

2.Improve the puzzle generator so that it can create more diverse puzzles, including melds with multiple 
special tiles.

3.Optimize or experiment with new algorithms to reduce program resource consumption.


# AI Usage Statement
In this project, I utilized AI to assist us in organizing our design ideas,
implementing certain specific programming syntax, and identifying and resolving errors.




