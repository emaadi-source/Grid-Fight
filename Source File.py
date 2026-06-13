
# IMPORTS & CONSTANTS


import random
import copy
import time 

# Cell types
EMPTY = '.'
OBSTACLE = 'X'
FORTRESS = 'F'
MINEFIELD = 'M'

# Agent labels
AGENT_A = 'A'
AGENT_B = 'B'
AGENT_C = 'C'

# Die probabilities (9-sided uneven die)
DIE_PROBABILITIES = {
    1: 0.10,
    2: 0.10,
    3: 0.15,
    4: 0.08,
    5: 0.08,
    6: 0.12,
    7: 0.13,
    8: 0.13,
    9: 0.11,
}

# Minefield probabilities
MINEFIELD_PROBABILITIES = {
    'safe_passage': 0.40,
    'energy_drain': 0.30,
    'unit_disabled': 0.20,
    'mine_detonation': 0.10,
}

# Agent capabilities
AGENT_CAPABILITIES = {
    AGENT_A: {
        'label': 'Expert',
        'depth': 7,       # Reduced for testing (original: 7)
        'vision_range': None,
        'chance_branches': 9,
        'eval_factors': 5,
        'transposition_table': True,
    },
    AGENT_B: {
        'label': 'Intermediate',
        'depth': 5,       # Reduced for testing (original: 5)
        'vision_range': 5,
        'chance_branches': 9,
        'eval_factors': 3,
        'transposition_table': False,
    },
    AGENT_C: {
        'label': 'Novice',
        'depth': 3,       # Reduced for testing (original: 3)
        'vision_range': 3,
        'chance_branches': 2,
        'eval_factors': 1,
        'transposition_table': False,
    },
}

# GAME STATE CLASS


class GameState:
    """Represents the complete state of the game at any point."""
    
    def __init__(self, grid, agents, scores, round_num, env_effects, 
                 eliminated, units_disabled):
        self.grid = grid
        self.agents = agents
        self.scores = scores
        self.round_num = round_num
        self.env_effects = env_effects
        self.eliminated = eliminated
        self.units_disabled = units_disabled
    
    def clone(self):
        """Deep copy the game state for search tree."""
        return copy.deepcopy(self)


#  BOARD LOADER


def load_board(filename):
    """Reads board.txt and returns grid, N, M, R, start_positions."""
    with open(filename, 'r') as f:
        lines = f.read().strip().split('\n')
    
    first_line = lines[0].split()
    N = int(first_line[0])
    M = int(first_line[1])
    R = int(first_line[2])
    
    grid = []
    for i in range(N):
        row_chars = lines[1 + i].split()
        row = []
        for ch in row_chars:
            cell = {
                'type': ch,
                'owner': None,
                'defense': 0,
            }
            row.append(cell)
        grid.append(row)
    
    a_coords = lines[1 + N].split()
    a_start = (int(a_coords[0]), int(a_coords[1]))
    
    b_coords = lines[2 + N].split()
    b_start = (int(b_coords[0]), int(b_coords[1]))
    
    c_coords = lines[3 + N].split()
    c_start = (int(c_coords[0]), int(c_coords[1]))
    
    start_positions = {
        AGENT_A: a_start,
        AGENT_B: b_start,
        AGENT_C: c_start,
    }
    
    return grid, N, M, R, start_positions


# INITIALIZE GAME


def initialize_game(grid, start_positions):
    """Sets up initial game state with 2 units per agent, energy=20."""
    agents = {}
    for agent_label in [AGENT_A, AGENT_B, AGENT_C]:
        pos = start_positions[agent_label]
        agents[agent_label] = {
            'units': [
                {'position': pos, 'active': True},
                {'position': pos, 'active': True}
            ],
            'energy': 20,
        }
        r, c = pos
        grid[r][c]['owner'] = agent_label
        grid[r][c]['defense'] = 1
    
    scores = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    env_effects = {}
    eliminated = set()
    units_disabled = {}
    
    state = GameState(grid, agents, scores, 1, env_effects, 
                      eliminated, units_disabled)
    return state


# HELPER FUNCTIONS


def get_adjacent_cells(pos, N, M):
    """Returns list of adjacent positions (up, down, left, right)."""
    r, c = pos
    adjacent = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < M:
            adjacent.append((nr, nc))
    return adjacent

def get_cell(state, pos):
    """Returns the cell dict at a position."""
    r, c = pos
    return state.grid[r][c]

def count_owned_cells(state, agent_label):
    """Counts how many cells an agent owns."""
    count = 0
    for row in state.grid:
        for cell in row:
            if cell['owner'] == agent_label:
                count += 1
    return count


# ACTION FUNCTIONS


def resolve_attack(state, attacker_label, target_pos):
    """Resolves an attack using the 9-sided die. Returns (msg, state)."""
    roll = random.choices(
        population=list(DIE_PROBABILITIES.keys()),
        weights=list(DIE_PROBABILITIES.values()),
        k=1
    )[0]
    
    target_cell = get_cell(state, target_pos)
    
    if roll in [1, 2]:
        state.agents[attacker_label]['energy'] = max(
            0, state.agents[attacker_label]['energy'] - 1
        )
        return f"Roll {roll}: Attack failed. Extra energy lost.", state
    elif roll == 3:
        return f"Roll {roll}: Attack failed. No extra loss.", state
    elif roll in [4, 5]:
        target_cell['owner'] = None
        target_cell['defense'] = 0
        return f"Roll {roll}: Partial success. Cell neutralized.", state
    elif roll == 6:
        target_cell['owner'] = None
        target_cell['defense'] = 0
        return f"Roll {roll}: Partial success + advance.", state
    elif roll in [7, 8]:
        target_cell['defense'] -= 1
        if target_cell['defense'] <= 0:
            target_cell['owner'] = attacker_label
            target_cell['defense'] = 1
            return f"Roll {roll}: Full success! Captured.", state
        return f"Roll {roll}: Full success. Defense reduced.", state
    elif roll == 9:
        target_cell['defense'] -= 1
        bonus = 0
        if target_cell['defense'] <= 0:
            target_cell['owner'] = attacker_label
            target_cell['defense'] = 1
            state.scores[attacker_label] += 2
            bonus = 2
        return f"Roll {roll}: CRITICAL HIT! Bonus: {bonus}", state
    return "Unknown outcome", state

def move_unit(state, agent_label, unit_index, target_pos):
    """Moves a unit. Handles empty capture, attack, minefield. Returns (msg, state)."""
    unit = state.agents[agent_label]['units'][unit_index]
    target_cell = get_cell(state, target_pos)
    
    if target_cell['type'] == OBSTACLE:
        return "Cannot move onto obstacle.", state
    
    if target_cell['type'] == MINEFIELD:
        mine_roll = random.choices(
            population=['safe', 'drain', 'disable', 'detonate'],
            weights=[0.40, 0.30, 0.20, 0.10],
            k=1
        )[0]
        if mine_roll == 'drain':
            state.agents[agent_label]['energy'] = max(
                0, state.agents[agent_label]['energy'] - 3
            )
        elif mine_roll == 'disable':
            state.units_disabled[(agent_label, unit_index)] = 2
        elif mine_roll == 'detonate':
            target_cell['type'] = OBSTACLE
            state.agents[agent_label]['energy'] = max(
                0, state.agents[agent_label]['energy'] - 5
            )
    
    if target_cell['owner'] is None and target_cell['type'] != OBSTACLE:
        unit['position'] = target_pos
        target_cell['owner'] = agent_label
        target_cell['defense'] = 1
        state.agents[agent_label]['energy'] -= 1
        return f"Moved to {target_pos}. Captured.", state
    elif target_cell['owner'] is not None and target_cell['owner'] != agent_label:
        unit['position'] = target_pos
        state.agents[agent_label]['energy'] -= 1
        outcome, state = resolve_attack(state, agent_label, target_pos)
        return f"Moved+Attack {target_pos}. {outcome}", state
    elif target_cell['owner'] == agent_label:
        unit['position'] = target_pos
        state.agents[agent_label]['energy'] -= 1
        return f"Moved to own cell {target_pos}.", state
    
    return "Unknown move outcome", state

def attack_cell(state, agent_label, unit_index, target_pos):
    """Attacks an adjacent cell without moving. Returns (msg, state)."""
    state.agents[agent_label]['energy'] -= 1
    outcome, state = resolve_attack(state, agent_label, target_pos)
    return f"Attacked {target_pos}. {outcome}", state

def fortify_cell(state, agent_label, target_pos):
    """Increases defense of owned adjacent cell. Returns (msg, state)."""
    target_cell = get_cell(state, target_pos)
    if target_cell['owner'] == agent_label and target_cell['defense'] < 3:
        target_cell['defense'] += 1
        state.agents[agent_label]['energy'] -= 1
        return f"Fortified {target_pos}. Defense={target_cell['defense']}.", state
    return f"Cannot fortify {target_pos}.", state

def wait_action(state, agent_label):
    """Does nothing, costs 1 energy. Returns (msg, state)."""
    state.agents[agent_label]['energy'] -= 1
    return "Waited.", state


# SECTION 7: SCORING & GAME END CHECK


def calculate_scores(state):
    """+1 per owned regular cell, +3 per owned fortress per round."""
    for row in state.grid:
        for cell in row:
            owner = cell['owner']
            if owner is not None:
                if cell['type'] == FORTRESS:
                    state.scores[owner] += 3
                else:
                    state.scores[owner] += 1
    return state

def check_game_end(state, R):
    """
    Checks: max rounds, 60% domination, eliminations.
    Returns (is_over, winner_or_None).
    """
    if state.round_num > R:
        return True, max(state.scores, key=state.scores.get)
    
    total_cells = 0
    owned_by = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    for row in state.grid:
        for cell in row:
            if cell['type'] != OBSTACLE:
                total_cells += 1
                if cell['owner'] is not None:
                    owned_by[cell['owner']] += 1
    
    for agent, count in owned_by.items():
        if total_cells > 0 and count / total_cells > 0.60:
            return True, agent
    
    active_agents = []
    for agent in [AGENT_A, AGENT_B, AGENT_C]:
        if agent not in state.eliminated:
            has_active = any(u['active'] for u in state.agents[agent]['units'])
            if not has_active or state.agents[agent]['energy'] <= 0:
                state.eliminated.add(agent)
            else:
                active_agents.append(agent)
    
    if len(active_agents) == 1:
        return True, active_agents[0]
    
    return False, None


#  ENVIRONMENTAL EVENTS


def apply_environmental_event(state):
    """Applies a random environmental event at start of round. Returns (msg, state)."""
    events = ['supply_drop', 'earthquake', 'reinforcement', 'fog_of_war']
    event = random.choice(events)
    N = len(state.grid)
    M = len(state.grid[0])
    
    if event == 'supply_drop':
        empty_cells = []
        for r in range(N):
            for c in range(M):
                if state.grid[r][c]['type'] == EMPTY and state.grid[r][c]['owner'] is None:
                    empty_cells.append((r, c))
        if empty_cells:
            pos = random.choice(empty_cells)
            state.grid[pos[0]][pos[1]]['type'] = FORTRESS
            state.grid[pos[0]][pos[1]]['defense'] = 2
            state.env_effects['supply_drop'] = (pos, 3)
            return f"Supply Drop: Fortress at {pos}", state
        return "Supply Drop: No empty cells", state
    
    elif event == 'earthquake':
        owned_cells = []
        for r in range(N):
            for c in range(M):
                if state.grid[r][c]['owner'] is not None:
                    owned_cells.append((r, c))
        if owned_cells:
            pos = random.choice(owned_cells)
            cell = state.grid[pos[0]][pos[1]]
            cell['defense'] -= 1
            if cell['defense'] <= 0:
                cell['owner'] = None
                cell['defense'] = 0
                return f"Earthquake: {pos} became neutral", state
            return f"Earthquake: {pos} defense reduced to {cell['defense']}", state
        return "Earthquake: No owned cells", state
    
    elif event == 'reinforcement':
        return "Reinforcement: Extra unit (simplified)", state
    
    elif event == 'fog_of_war':
        return "Fog of War: Vision halved", state
    
    return "Unknown event", state


#  EVALUATION FUNCTION


def evaluate_state(state, agent_label, num_factors):
    """
    Evaluation function with configurable complexity.
    1 = greedy (score diff), 3 = intermediate, 5 = expert.
    """
    opponent_labels = [l for l in [AGENT_A, AGENT_B, AGENT_C] if l != agent_label]
    avg_opp_score = sum(state.scores[o] for o in opponent_labels) / 2.0
    
    # Factor 1: Score differential
    score_diff = state.scores[agent_label] - avg_opp_score
    
    if num_factors == 1:
        return score_diff
    
    # Factor 2: Territory control
    my_cells = 0
    my_fortresses = 0
    for row in state.grid:
        for cell in row:
            if cell['owner'] == agent_label:
                my_cells += 1
                if cell['type'] == FORTRESS:
                    my_fortresses += 1
    territory_score = my_cells + (my_fortresses * 3)
    
    # Factor 3: Energy advantage
    my_energy = state.agents[agent_label]['energy']
    avg_opp_energy = sum(state.agents[o]['energy'] for o in opponent_labels) / 2.0
    energy_adv = my_energy - avg_opp_energy
    
    if num_factors == 3:
        return (0.5 * score_diff) + (0.3 * territory_score) + (0.2 * energy_adv)
    
    # Factor 4: Positional advantage
    positional_score = 0
    my_units = [u for u in state.agents[agent_label]['units'] if u['active']]
    for unit in my_units:
        ur, uc = unit['position']
        for r in range(len(state.grid)):
            for c in range(len(state.grid[0])):
                cell = state.grid[r][c]
                dist = abs(ur - r) + abs(uc - c)
                if dist == 0:
                    continue
                if cell['type'] == FORTRESS and cell['owner'] != agent_label:
                    positional_score += 2.0 / (dist + 1)
                elif cell['owner'] != agent_label:
                    positional_score += 0.5 / (dist + 1)
    
    # Factor 5: Threat assessment
    threat_penalty = 0
    for opp_label in opponent_labels:
        opp_units = [u for u in state.agents[opp_label]['units'] if u['active']]
        for unit in opp_units:
            ur, uc = unit['position']
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = ur + dr, uc + dc
                if 0 <= nr < len(state.grid) and 0 <= nc < len(state.grid[0]):
                    if state.grid[nr][nc]['owner'] == agent_label:
                        threat_penalty += 1
    
    evaluation = (0.30 * score_diff) + (0.20 * territory_score) + \
                 (0.15 * energy_adv) + (0.20 * positional_score) - \
                 (0.15 * threat_penalty)
    return evaluation


#  GET POSSIBLE ACTIONS


def get_possible_actions(state, agent_label):
    """Returns limited list of actions for search (one unit per turn)."""
    actions = []
    N = len(state.grid)
    M = len(state.grid[0])
    
    if agent_label in state.eliminated:
        return [('wait', 0, None)]
    
    agent_data = state.agents[agent_label]
    if agent_data['energy'] <= 0:
        return [('wait', 0, None)]
    
    active_unit_idx = None
    for i, unit in enumerate(agent_data['units']):
        if not unit['active']:
            continue
        if (agent_label, i) in state.units_disabled:
            if state.units_disabled[(agent_label, i)] > 0:
                continue
        active_unit_idx = i
        break
    
    if active_unit_idx is None:
        return [('wait', 0, None)]
    
    pos = agent_data['units'][active_unit_idx]['position']
    adjacent = get_adjacent_cells(pos, N, M)
    
    for adj in adjacent:
        cell = state.grid[adj[0]][adj[1]]
        if cell['type'] != OBSTACLE:
            actions.append(('move', active_unit_idx, adj))
    
    for adj in adjacent:
        cell = state.grid[adj[0]][adj[1]]
        if cell['owner'] is not None and cell['owner'] != agent_label:
            actions.append(('attack', active_unit_idx, adj))
    
    for adj in adjacent:
        cell = state.grid[adj[0]][adj[1]]
        if cell['owner'] == agent_label and cell['defense'] < 3:
            actions.append(('fortify', active_unit_idx, adj))
    
    actions.append(('wait', 0, None))
    
    # Move ordering: better moves first for alpha-beta efficiency
    def action_priority(a):
        if a[0] == 'move':
            target_cell = state.grid[a[2][0]][a[2][1]]
            if target_cell['owner'] is None:
                return 0
            elif target_cell['type'] == FORTRESS:
                return 1
            else:
                return 2
        elif a[0] == 'attack':
            target_cell = state.grid[a[2][0]][a[2][1]]
            if target_cell['type'] == FORTRESS:
                return 3
            else:
                return 4
        elif a[0] == 'fortify':
            return 5
        else:
            return 6
    
    actions.sort(key=action_priority)
    return actions



def apply_action(state, agent_label, action):
    """Applies action to a cloned state. Returns new state."""
    new_state = state.clone()
    action_type, unit_idx, target = action
    
    if action_type == 'move':
        _, new_state = move_unit(new_state, agent_label, unit_idx, target)
    elif action_type == 'attack':
        _, new_state = attack_cell(new_state, agent_label, unit_idx, target)
    elif action_type == 'fortify':
        _, new_state = fortify_cell(new_state, agent_label, target)
    elif action_type == 'wait':
        _, new_state = wait_action(new_state, agent_label)
    
    # Decrement disabled unit counters
    to_remove = []
    for (ag, uid), turns in new_state.units_disabled.items():
        if turns > 0:
            new_state.units_disabled[(ag, uid)] = turns - 1
        if new_state.units_disabled[(ag, uid)] <= 0:
            to_remove.append((ag, uid))
    for key in to_remove:
        del new_state.units_disabled[key]
    
    return new_state


# EXPECTIMINIMAX WITH ALPHA-BETA


nodes_explored = 0
nodes_pruned = 0
MAX_NODES = 10000

def reset_counters():
    global nodes_explored, nodes_pruned
    nodes_explored = 0
    nodes_pruned = 0

def get_chance_branches(agent_label):
    """Returns die faces to consider based on agent capability."""
    num_branches = AGENT_CAPABILITIES[agent_label]['chance_branches']
    if num_branches >= 9:
        return [7, 8, 9, 3, 6, 4, 5, 1, 2]
    elif num_branches == 2:
        return [7, 8]
    return [7, 8]

def expectiminimax(state, depth, agent_label, alpha, beta, is_maximizer, 
                   original_agent, chance_branches):
    """Expectiminimax with alpha-beta pruning and node limit."""
    global nodes_explored, nodes_pruned
    nodes_explored += 1
    
    if nodes_explored > MAX_NODES:
        num_factors = AGENT_CAPABILITIES[original_agent]['eval_factors']
        return evaluate_state(state, original_agent, num_factors), None
    
    is_over, winner = check_game_end(state, 30)
    if is_over or depth <= 0:
        if winner == original_agent:
            return 10000, None
        elif winner is not None:
            return -10000, None
        num_factors = AGENT_CAPABILITIES[original_agent]['eval_factors']
        return evaluate_state(state, original_agent, num_factors), None
    
    actions = get_possible_actions(state, agent_label)
    if not actions:
        num_factors = AGENT_CAPABILITIES[original_agent]['eval_factors']
        return evaluate_state(state, original_agent, num_factors), None
    
    actions = actions[:4]  # Limit to top 4 actions
    
    if is_maximizer:
        best_value = float('-inf')
        best_action = actions[0]
        
        for action in actions:
            if nodes_explored > MAX_NODES:
                break
            
            new_state = apply_action(state, agent_label, action)
            
            opponents = [a for a in [AGENT_A, AGENT_B, AGENT_C] 
                       if a != original_agent and a not in new_state.eliminated]
            
            if not opponents:
                num_factors = AGENT_CAPABILITIES[original_agent]['eval_factors']
                child_val = evaluate_state(new_state, original_agent, num_factors)
            else:
                min_val = float('inf')
                for opp in opponents[:2]:  # Limit opponents
                    val, _ = expectiminimax(
                        new_state, depth-1, opp,
                        float('-inf'), float('inf'),
                        False, original_agent, chance_branches
                    )
                    min_val = min(min_val, val)
                child_val = min_val
            
            if child_val > best_value:
                best_value = child_val
                best_action = action
            
            alpha = max(alpha, best_value)
            if best_value >= beta:
                nodes_pruned += 1
                return best_value, best_action
        
        return best_value, best_action
    
    else:
        best_value = float('inf')
        best_action = actions[0]
        
        for action in actions:
            if nodes_explored > MAX_NODES:
                break
            
            new_state = apply_action(state, agent_label, action)
            
            all_agents = [AGENT_A, AGENT_B, AGENT_C]
            current_idx = all_agents.index(agent_label)
            next_idx = (current_idx + 1) % 3
            next_agent = all_agents[next_idx]
            
            if next_agent in new_state.eliminated:
                next_idx = (next_idx + 1) % 3
                next_agent = all_agents[next_idx]
            
            next_is_max = (next_agent == original_agent)
            
            val, _ = expectiminimax(
                new_state, depth-1, next_agent,
                alpha, beta, next_is_max, original_agent, chance_branches
            )
            
            if val < best_value:
                best_value = val
                best_action = action
            
            beta = min(beta, best_value)
            if best_value <= alpha:
                nodes_pruned += 1
                return best_value, best_action
        
        return best_value, best_action

def get_best_action(state, agent_label):
    """Wrapper that calls expectiminimax and returns best action."""
    global nodes_explored, nodes_pruned
    reset_counters()
    
    capabilities = AGENT_CAPABILITIES[agent_label]
    depth = capabilities['depth']
    chance_branches = get_chance_branches(agent_label)
    
    value, action = expectiminimax(
        state, depth, agent_label,
        float('-inf'), float('inf'),
        True, agent_label,
        chance_branches
    )
    
    return action, value, nodes_explored, nodes_pruned

# MOVE LOGGING


move_log = []

def log_move(move_num, agent_label, action, nodes_exp, nodes_pruned, utility):
    """Logs a move to console and memory."""
    capabilities = AGENT_CAPABILITIES[agent_label]
    agent_name = capabilities['label']
    action_desc = f"{action[0].capitalize()} {action[2]}" if action[2] else action[0].capitalize()
    
    pruned_pct = (nodes_pruned / nodes_exp * 100) if nodes_exp > 0 else 0
    
    log_entry = (
        f"Move {move_num} | Agent {agent_label} ({agent_name}) | "
        f"Action: {action_desc}\n"
        f"  Expectiminimax nodes explored: {nodes_exp}\n"
        f"  Nodes pruned (Alpha-Beta): {nodes_pruned} ({pruned_pct:.1f}%)\n"
        f"  Chosen action value (utility): {utility:.2f}"
    )
    
    print(log_entry)
    print()
    move_log.append(log_entry)

def write_results_to_file(filename, final_winner, final_scores, total_nodes, total_pruned):
    """Writes all logs and final results to results.txt."""
    with open(filename, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("STOCHASTIC BATTLEFIELD GAME - RESULTS\n")
        f.write("=" * 60 + "\n\n")
        
        for entry in move_log:
            f.write(entry + "\n\n")
        
        f.write("=" * 60 + "\n")
        f.write(f"GAME OVER - Winner: Agent {final_winner}\n")
        f.write(f"Final Scores: {final_scores}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("NODE EXPLORATION SUMMARY\n")
        f.write("-" * 40 + "\n")
        for ag in [AGENT_A, AGENT_B, AGENT_C]:
            tn = total_nodes[ag]
            tp = total_pruned[ag]
            eff = (tp / tn * 100) if tn > 0 else 0
            f.write(f"Agent {ag} ({AGENT_CAPABILITIES[ag]['label']}): "
                   f"Explored={tn}, Pruned={tp}, Efficiency={eff:.1f}%\n")


#  MAIN GAME LOOP


def run_game_console(board_file="board.txt", max_rounds=30):
    """Runs a full game in console mode."""
    global move_log
    move_log = []
    
    print("\n" + "=" * 60)
    print("STARTING STOCHASTIC BATTLEFIELD GAME")
    print("=" * 60 + "\n")
    
    grid, N, M, R, start_positions = load_board(board_file)
    state = initialize_game(grid, start_positions)
    R = min(R, max_rounds)
    
    move_number = 0
    total_nodes = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    total_pruned = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    
    turn_order = [AGENT_A, AGENT_B, AGENT_C]
    
    while state.round_num <= R:
        print(f"\n{'='*40}")
        print(f"ROUND {state.round_num}")
        print(f"{'='*40}")
        
        # Environmental event
        event_msg, state = apply_environmental_event(state)
        print(f"Event: {event_msg}")
        
        for agent_label in turn_order:
            if agent_label in state.eliminated:
                continue
            
            if state.agents[agent_label]['energy'] <= 0:
                state.agents[agent_label]['energy'] = 0
                move_number += 1
                log_move(move_number, agent_label, ('wait', 0, None), 0, 0, 0)
                continue
            
            print(f"\n{agent_label} ({AGENT_CAPABILITIES[agent_label]['label']}) thinking...")
            action, utility, nodes_exp, nodes_pruned = get_best_action(state, agent_label)
            
            move_number += 1
            total_nodes[agent_label] += nodes_exp
            total_pruned[agent_label] += nodes_pruned
            
            # Apply action
            if action[0] == 'move':
                msg, state = move_unit(state, agent_label, action[1], action[2])
            elif action[0] == 'attack':
                msg, state = attack_cell(state, agent_label, action[1], action[2])
            elif action[0] == 'fortify':
                msg, state = fortify_cell(state, agent_label, action[2])
            else:
                msg, state = wait_action(state, agent_label)
            
            print(f"Action: {action} -> {msg}")
            
            log_move(move_number, agent_label, action, nodes_exp, nodes_pruned, utility)
            
            is_over, winner = check_game_end(state, R)
            if is_over:
                print(f"\n{'='*60}")
                print(f"GAME OVER! Winner: Agent {winner}")
                print(f"Final Scores: {state.scores}")
                print(f"{'='*60}")
                
                write_results_to_file("results.txt", winner, state.scores, total_nodes, total_pruned)
                print("\nResults written to results.txt")
                return winner, state.scores
        
        state = calculate_scores(state)
        print(f"\nEnd of round {state.round_num} scores: {state.scores}")
        state.round_num += 1
        
        if move_number > 200:
            print("Move limit reached.")
            break
    
    winner = max(state.scores, key=state.scores.get)
    print(f"\n{'='*60}")
    print(f"GAME OVER! Winner: Agent {winner}")
    print(f"Final Scores: {state.scores}")
    print(f"{'='*60}")
    
    write_results_to_file("results.txt", winner, state.scores, total_nodes, total_pruned)
    return winner, state.scores



#  DEAR PYGUI GUI


import dearpygui.dearpygui as dpg

# GUI State variables
gui_state = None
gui_board_file = "board.txt"
gui_max_rounds = 30
gui_move_number = 0
gui_total_nodes = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
gui_total_pruned = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
gui_auto_play = False
gui_auto_speed = 0.5  # seconds between moves
gui_game_over = False

def build_gui():
    """Creates the Dear PyGui interface."""
    dpg.create_context()
    
    # Color theme
    agent_colors = {
        AGENT_A: (255, 100, 100),    # Red
        AGENT_B: (100, 100, 255),    # Blue
        AGENT_C: (100, 255, 100),    # Green
        'F': (255, 215, 0),          # Gold for Fortress
        'X': (60, 60, 60),           # Dark gray for Obstacle
        'M': (255, 165, 0),          # Orange for Minefield
        EMPTY: (200, 200, 200),      # Light gray for Empty
    }
    
    # Main window
    with dpg.window(label="Stochastic Battlefield Game", tag="main_window",
                    width=1200, height=800):
        
        with dpg.group(horizontal=True):
            # Left side: Board
            with dpg.child_window(width=650, height=750, tag="board_panel"):
                dpg.add_text("Game Board", tag="board_title")
                dpg.add_separator()
                # Board will be drawn dynamically
                with dpg.group(tag="board_grid"):
                    pass
            
            # Right side: Info panel
            with dpg.child_window(width=530, height=750, tag="info_panel"):
                dpg.add_text("Game Information", tag="info_title")
                dpg.add_separator()
                
                # Scores section
                with dpg.collapsing_header(label="Scores & Stats", default_open=True):
                    dpg.add_text("Round: 0", tag="round_text")
                    dpg.add_text("Move: 0", tag="move_text")
                    dpg.add_separator()
                    
                    for agent in [AGENT_A, AGENT_B, AGENT_C]:
                        cap = AGENT_CAPABILITIES[agent]
                        with dpg.group(tag=f"agent_{agent}_info"):
                            dpg.add_text(f"Agent {agent} ({cap['label']})", 
                                        color=agent_colors[agent])
                            dpg.add_text(f"  Score: 0", tag=f"score_{agent}")
                            dpg.add_text(f"  Energy: 20", tag=f"energy_{agent}")
                            dpg.add_text(f"  Cells: 1", tag=f"cells_{agent}")
                            dpg.add_text(f"  Active Units: 2", tag=f"units_{agent}")
                            dpg.add_separator()
                
                # Move log
                with dpg.collapsing_header(label="Move Log", default_open=True):
                    dpg.add_text("Game starting...", tag="move_log_text", 
                                wrap=500)
                
                # Node stats
                with dpg.collapsing_header(label="Node Statistics", default_open=True):
                    for agent in [AGENT_A, AGENT_B, AGENT_C]:
                        dpg.add_text(f"Agent {agent}: Explored=0, Pruned=0, Eff=0%",
                                    tag=f"stats_{agent}")
                
                dpg.add_separator()
                
                # Control buttons
                with dpg.group(label="Controls"):
                    dpg.add_text("Controls:")
                    dpg.add_button(label="Start New Game", callback=start_new_game,
                                  width=200, height=30)
                    dpg.add_button(label="Next Move", callback=next_move_gui,
                                  width=200, height=30, tag="next_btn")
                    dpg.add_button(label="Run", callback=toggle_auto_play,
                                  width=200, height=30, tag="run_btn")
                    dpg.add_button(label="Pause", callback=stop_auto_play,
                                  width=200, height=30, tag="pause_btn")
                    dpg.add_slider_int(label="Speed", default_value=5, min_value=1,
                                      max_value=10, tag="speed_slider", width=200)
                    dpg.add_text("Speed: 1=slow, 10=fast", tag="speed_label")
    
    dpg.create_viewport(title="Stochastic Battlefield - Expectiminimax", 
                       width=1220, height=820)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

def draw_board(state):
    """Draws the game board grid."""
    if not dpg.does_item_exist("board_grid"):
        return
    
    # Clear old board
    dpg.delete_item("board_grid", children_only=True)
    
    N = len(state.grid)
    M = len(state.grid[0])
    cell_size = min(500 // max(N, M), 50)
    
    agent_colors = {
        AGENT_A: (255, 100, 100),
        AGENT_B: (100, 100, 255),
        AGENT_C: (100, 255, 100),
        None: (200, 200, 200),
    }
    
    type_colors = {
        FORTRESS: (255, 215, 0),
        OBSTACLE: (60, 60, 60),
        MINEFIELD: (255, 165, 0),
        EMPTY: (200, 200, 200),
    }
    
    with dpg.group(horizontal=True, parent="board_grid"):
        for r in range(N):
            with dpg.group():
                for c in range(M):
                    cell = state.grid[r][c]
                    
                    # Determine color
                    if cell['type'] == OBSTACLE:
                        color = type_colors[OBSTACLE]
                    elif cell['owner'] is not None:
                        color = agent_colors[cell['owner']]
                    else:
                        color = type_colors.get(cell['type'], (200, 200, 200))
                    
                    # Label
                    if cell['type'] == OBSTACLE:
                        label = "X"
                    elif cell['type'] == FORTRESS:
                        label = f"F{cell['defense']}"
                    elif cell['type'] == MINEFIELD:
                        label = "M"
                    elif cell['owner'] is not None:
                        label = f"{cell['owner']}{cell['defense']}"
                    else:
                        label = "."
                    
                    # Draw cell
                    cell_tag = f"cell_{r}_{c}"
                    with dpg.group(horizontal=False):
                        dpg.add_button(label=label, tag=cell_tag,
                                      width=cell_size, height=cell_size,
                                      enabled=False)
                        # Color the button
                        with dpg.theme() as cell_theme:
                            with dpg.theme_component(dpg.mvButton):
                                dpg.add_theme_color(dpg.mvThemeCol_Button, 
                                                   tuple(c/255 for c in color), 
                                                   category=dpg.mvThemeCat_Core)
                        dpg.bind_item_theme(cell_tag, cell_theme)

def update_info_panel(state, round_num, move_num):
    """Updates the right-side info panel."""
    if not dpg.does_item_exist("round_text"):
        return
    
    dpg.set_value("round_text", f"Round: {round_num}")
    dpg.set_value("move_text", f"Move: {move_num}")
    
    for agent in [AGENT_A, AGENT_B, AGENT_C]:
        dpg.set_value(f"score_{agent}", f"  Score: {state.scores[agent]}")
        dpg.set_value(f"energy_{agent}", f"  Energy: {state.agents[agent]['energy']}")
        owned = count_owned_cells(state, agent)
        dpg.set_value(f"cells_{agent}", f"  Cells: {owned}")
        active = sum(1 for u in state.agents[agent]['units'] if u['active'])
        dpg.set_value(f"units_{agent}", f"  Active Units: {active}")
        
        tn = gui_total_nodes[agent]
        tp = gui_total_pruned[agent]
        eff = (tp/tn*100) if tn > 0 else 0
        dpg.set_value(f"stats_{agent}", 
                     f"Agent {agent}: Explored={tn}, Pruned={tp}, Eff={eff:.1f}%")

def update_move_log(message):
    """Adds message to move log."""
    if dpg.does_item_exist("move_log_text"):
        dpg.set_value("move_log_text", message)

def start_new_game(sender, app_data, user_data):
    """Initializes a new game from board.txt."""
    global gui_state, gui_move_number, gui_total_nodes, gui_total_pruned
    global gui_game_over
    
    grid, N, M, R, start_positions = load_board(gui_board_file)
    gui_state = initialize_game(grid, start_positions)
    gui_state.round_num = 1
    gui_move_number = 0
    gui_total_nodes = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    gui_total_pruned = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    gui_game_over = False
    
    draw_board(gui_state)
    update_info_panel(gui_state, 1, 0)
    update_move_log("New game started! Press 'Next Move' to begin.")
    dpg.set_value("run_btn", "Run")

def process_one_move():
    """Processes one move in the game. Returns True if game continues."""
    global gui_state, gui_move_number, gui_total_nodes, gui_total_pruned
    global gui_game_over
    
    if gui_state is None or gui_game_over:
        return False
    
    # Apply environmental event at start of each round
    if gui_move_number % 3 == 0:
        event_msg, gui_state = apply_environmental_event(gui_state)
        update_move_log(f"Round {gui_state.round_num}: {event_msg}")
    
    # Determine which agent moves
    turn_order = [AGENT_A, AGENT_B, AGENT_C]
    agent_idx = gui_move_number % 3
    agent_label = turn_order[agent_idx]
    
    if agent_label in gui_state.eliminated:
        gui_move_number += 1
        return True
    
    if gui_state.agents[agent_label]['energy'] <= 0:
        gui_state.agents[agent_label]['energy'] = 0
        gui_move_number += 1
        update_move_log(f"Agent {agent_label}: No energy. Waits.")
        return True
    
    # Get and apply action
    action, utility, nodes_exp, nodes_pruned = get_best_action(gui_state, agent_label)
    
    gui_total_nodes[agent_label] += nodes_exp
    gui_total_pruned[agent_label] += nodes_pruned
    gui_move_number += 1
    
    if action[0] == 'move':
        msg, gui_state = move_unit(gui_state, agent_label, action[1], action[2])
    elif action[0] == 'attack':
        msg, gui_state = attack_cell(gui_state, agent_label, action[1], action[2])
    elif action[0] == 'fortify':
        msg, gui_state = fortify_cell(gui_state, agent_label, action[2])
    else:
        msg, gui_state = wait_action(gui_state, agent_label)
    
    cap = AGENT_CAPABILITIES[agent_label]
    log_msg = (f"Move {gui_move_number} | Agent {agent_label} ({cap['label']})\n"
              f"  Action: {action[0]} {action[2] if action[2] else ''}\n"
              f"  Nodes: {nodes_exp} explored, {nodes_pruned} pruned\n"
              f"  Utility: {utility:.2f}\n"
              f"  Result: {msg}")
    update_move_log(log_msg)
    
    # End of round scoring
    if gui_move_number % 3 == 0:
        gui_state = calculate_scores(gui_state)
        gui_state.round_num += 1
    
    # Check game end
    is_over, winner = check_game_end(gui_state, gui_max_rounds)
    if is_over:
        gui_game_over = True
        update_move_log(f"GAME OVER! Winner: Agent {winner}\n"
                       f"Final Scores: {gui_state.scores}")
    
    draw_board(gui_state)
    update_info_panel(gui_state, gui_state.round_num, gui_move_number)
    
    return not gui_game_over

def next_move_gui(sender, app_data, user_data):
    """Callback: Process one move."""
    process_one_move()

def toggle_auto_play(sender, app_data, user_data):
    """Starts auto-play."""
    global gui_auto_play
    gui_auto_play = True
    dpg.set_value("run_btn", "Running...")

def stop_auto_play(sender, app_data, user_data):
    """Stops auto-play."""
    global gui_auto_play
    gui_auto_play = False
    dpg.set_value("run_btn", "Run")

def run_gui():
    """Main GUI loop with auto-play support."""
    global gui_auto_play, gui_state
    
    build_gui()
    
    # Initialize with a new game
    if gui_state is None:
        grid, N, M, R, start_positions = load_board(gui_board_file)
        gui_state = initialize_game(grid, start_positions)
        draw_board(gui_state)
        update_info_panel(gui_state, 1, 0)
    
    auto_timer = 0
    timer_interval = 0.5
    
    while dpg.is_dearpygui_running():
        # Handle auto-play
        if gui_auto_play and not gui_game_over:
            speed_val = dpg.get_value("speed_slider")
            timer_interval = 1.0 / speed_val  # 1=1s, 10=0.1s
            
            import time
            current_time = time.time()
            if current_time - auto_timer >= timer_interval:
                auto_timer = current_time
                if not process_one_move():
                    gui_auto_play = False
                    dpg.set_value("run_btn", "Run")
        
        dpg.render_dearpygui_frame()
    
    dpg.destroy_context()


#  STATISTICAL ANALYSIS


def run_statistical_analysis(board_file="board.txt", num_runs=5, max_rounds=20):
    """
    Runs multiple games and collects statistics.
    Returns a dict with all stats for the report.
    """
    print("\n" + "=" * 60)
    print(f"RUNNING {num_runs}-GAME STATISTICAL ANALYSIS")
    print("=" * 60)
    
    all_results = []
    win_counts = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
    total_scores = {AGENT_A: [], AGENT_B: [], AGENT_C: []}
    total_nodes_avg = {AGENT_A: [], AGENT_B: [], AGENT_C: []}
    total_pruned_avg = {AGENT_A: [], AGENT_B: [], AGENT_C: []}
    
    for run_id in range(1, num_runs + 1):
        print(f"\n--- Run {run_id}/{num_runs} ---")
        
        # Reset global move log
        global move_log
        move_log = []
        
        # Load fresh board each run
        grid, N, M, R, start_positions = load_board(board_file)
        state = initialize_game(grid, start_positions)
        R = min(R, max_rounds)
        
        move_number = 0
        run_nodes = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
        run_pruned = {AGENT_A: 0, AGENT_B: 0, AGENT_C: 0}
        
        turn_order = [AGENT_A, AGENT_B, AGENT_C]
        
        while state.round_num <= R:
            # Environmental event
            _, state = apply_environmental_event(state)
            
            for agent_label in turn_order:
                if agent_label in state.eliminated:
                    continue
                
                if state.agents[agent_label]['energy'] <= 0:
                    state.agents[agent_label]['energy'] = 0
                    move_number += 1
                    continue
                
                action, utility, nodes_exp, nodes_pruned = get_best_action(state, agent_label)
                
                move_number += 1
                run_nodes[agent_label] += nodes_exp
                run_pruned[agent_label] += nodes_pruned
                
                # Apply action
                if action[0] == 'move':
                    _, state = move_unit(state, agent_label, action[1], action[2])
                elif action[0] == 'attack':
                    _, state = attack_cell(state, agent_label, action[1], action[2])
                elif action[0] == 'fortify':
                    _, state = fortify_cell(state, agent_label, action[2])
                else:
                    _, state = wait_action(state, agent_label)
                
                # Check game end
                is_over, winner = check_game_end(state, R)
                if is_over:
                    break
            
            if is_over:
                break
            
            state = calculate_scores(state)
            state.round_num += 1
        
        # Record results
        if not is_over:
            winner = max(state.scores, key=state.scores.get)
        
        win_counts[winner] += 1
        for ag in [AGENT_A, AGENT_B, AGENT_C]:
            total_scores[ag].append(state.scores[ag])
            total_nodes_avg[ag].append(run_nodes[ag])
            total_pruned_avg[ag].append(run_pruned[ag])
        
        all_results.append({
            'run': run_id,
            'winner': winner,
            'scores': dict(state.scores),
            'nodes': dict(run_nodes),
            'pruned': dict(run_pruned),
        })
        
        print(f"  Winner: Agent {winner}, Scores: {state.scores}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("STATISTICAL ANALYSIS SUMMARY")
    print("=" * 60)
    
    print("\n--- Win Rates ---")
    for ag in [AGENT_A, AGENT_B, AGENT_C]:
        rate = (win_counts[ag] / num_runs) * 100
        print(f"Agent {ag} ({AGENT_CAPABILITIES[ag]['label']}): {win_counts[ag]}/{num_runs} ({rate:.0f}%)")
    
    print("\n--- Average Final Scores ---")
    for ag in [AGENT_A, AGENT_B, AGENT_C]:
        avg = sum(total_scores[ag]) / num_runs
        print(f"Agent {ag}: {avg:.1f}")
    
    print("\n--- Average Nodes Explored Per Game ---")
    for ag in [AGENT_A, AGENT_B, AGENT_C]:
        avg = sum(total_nodes_avg[ag]) / num_runs
        print(f"Agent {ag}: {avg:.0f}")
    
    print("\n--- Average Pruning Efficiency ---")
    for ag in [AGENT_A, AGENT_B, AGENT_C]:
        total_n = sum(total_nodes_avg[ag])
        total_p = sum(total_pruned_avg[ag])
        eff = (total_p / total_n * 100) if total_n > 0 else 0
        print(f"Agent {ag}: {eff:.1f}%")
    
    return {
        'win_counts': win_counts,
        'avg_scores': {ag: sum(total_scores[ag])/num_runs for ag in [AGENT_A, AGENT_B, AGENT_C]},
        'avg_nodes': {ag: sum(total_nodes_avg[ag])/num_runs for ag in [AGENT_A, AGENT_B, AGENT_C]},
        'pruning_eff': {ag: (sum(total_pruned_avg[ag])/sum(total_nodes_avg[ag])*100) 
                       if sum(total_nodes_avg[ag]) > 0 else 0 
                       for ag in [AGENT_A, AGENT_B, AGENT_C]},
    }


# CHOOSE MODE


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'console':
            print("=" * 50)
            print("CONSOLE MODE - 5 ROUNDS")
            print("=" * 50)
            winner, scores = run_game_console("board.txt", max_rounds=5)
            print(f"\nDone! Winner: Agent {winner}")
        
        elif sys.argv[1] == 'stats':
            print("=" * 50)
            print("RUNNING 5-GAME STATISTICAL ANALYSIS")
            print("=" * 50)
            stats = run_statistical_analysis("board.txt", num_runs=5, max_rounds=15)
            print("\nAnalysis complete! Use these numbers in your report.")
        
        elif sys.argv[1] == 'gui':
            print("Launching GUI...")
            run_gui()
    else:
        # Default: run GUI
        print("Launching GUI...")
        print("Use: python assignment3.py console | stats | gui")
        run_gui()