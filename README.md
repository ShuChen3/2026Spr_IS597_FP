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

After running test.py in profile mode, I found that the most frequently called function is _tile_matches_requirement(). 
The functions that take the most total running time are backtrack() in solver.py, dfs() in candidate_generator.py, 
and _find_run_assignment() in validator.py.

The solver needs to search through many possible combinations of candidate melds, so the backtracking function 
becomes one of the most time-consuming parts. The candidate generator also uses DFS to explore possible run paths 
in the graph, which can create many candidate combinations. In addition, run validation is more complex than 
group validation because it needs to check possible start values, colors, Joker assignments, Prism Joker assignments, 
and Rainbow King placement. Therefore, _find_run_assignment() and _tile_matches_requirement() are called many times 
during the validation process.


# Future improvment
1.Enable players to customize more game rules through parameters, such as the number of tile colors, 
the range of tile values, and special tile rules.

2.Improve the puzzle generator so that it can create more diverse puzzles, including melds with multiple 
special tiles.

3.Optimize or experiment with new algorithms to reduce program resource consumption.


# AI Usage Statement
In this project, I utilized AI to assist us in organizing our design ideas,
implementing certain specific programming syntax, and identifying and resolving errors.
https://chatgpt.com/share/69f6a266-1204-83ea-ae90-3c55869ba58d




