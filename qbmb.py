"""
Queen-bee and Mutant-bee evolution for genetic algorithms - Jung 2007

4 years after proposing the Queen bee evolution genetic algorithm, Jung proposes a simplification to get rid of a few hyperparameters

In the new scheme, all the selected bees to mate with the queen undergo strong mutation prior to crossover
This scheme therefore better preserves the queen's genetic code. He shows through various experiments that this performs just as well as the original algorithm while being simpler

https://www.researchgate.net/publication/290131255_Queen-bee_and_Mutant-bee_Evolution_for_Genetic_Algorithms
"""

import torch

# constants

GOAL = 'Attention is all you need'

POP_SIZE = 100
MUTATION_PROB = 0.04
STRONG_MUTATION_PROB = 0.25
NUM_TOURNAMENT_PARTICIPANTS = 25

# encode and decode functions

def encode(s):
    return torch.tensor([ord(c) for c in s])

def decode(t):
    return ''.join([chr(i) for i in t.tolist()])

# derived constants

gene_length = len(GOAL)
gene_midpoint = gene_length // 2
target_gene = encode(GOAL)

num_code_mutate = MUTATION_PROB * gene_length
strong_num_code_mutate = STRONG_MUTATION_PROB * gene_length

# queen bee genetic algorithm

generation = 1

pool = torch.randint(0, 255, (POP_SIZE, gene_length))

queen = queen_fitness = None

while True:
    print(f"\n\ngeneration {generation}\n")

    # sort population by fitness

    fitnesses = 1. / torch.square(pool - target_gene).sum(dim = -1)

    indices = fitnesses.sort(descending = True).indices
    pool, fitnesses = pool[indices], fitnesses[indices]

    # display every generation

    if queen is not None:
        print("queen:")
        print(f"{decode(queen)} ({queen_fitness.item():.3f})\n")

    for gene, fitness in zip(pool, fitnesses):
        print(f"{decode(gene)} ({fitness.item():.3f})")

    # solved if any fitness is inf

    if (fitnesses == float('inf')).any():
        break
    
    # if one of the children has a better fitness than queen, that child becomes the new queen
    # and the queen replaces the worst bee in the population, kept around for at least one generation more

    if queen is not None and queen_fitness < fitnesses[0]:
        pool = torch.cat((pool, queen[None, :]), dim = 0)
        fitnesses = torch.cat((fitnesses, queen_fitness[None]), dim = 0)
        queen = queen_fitness = None

    # separate the queen bee from the rest of the population

    if queen is None:
        queen, pool = pool[0], pool[1:]
        queen_fitness, fitnesses = fitnesses[0], fitnesses[1:]

    # deterministic tournament selection - let top winner become parent with queen

    contender_ids = torch.randn((POP_SIZE - 1, POP_SIZE - 1)).argsort(dim = -1)[..., :NUM_TOURNAMENT_PARTICIPANTS]
    participants, tournaments = pool[contender_ids], fitnesses[contender_ids]
    top_winner = tournaments.topk(1, dim = -1, largest = True, sorted = False).indices
    top_winner = top_winner.unsqueeze(-1).expand(-1, -1, gene_length)
    parents = participants.gather(1, top_winner).squeeze(1)

    # potential parents with queen is strongly mutated ("Mutant Bee")

    strong_mutate_mask = torch.randn(parents.shape).argsort(dim = -1) < strong_num_code_mutate
    noise = torch.randint(0, 2, parents.shape) * 2 - 1
    mutated_parents = torch.where(strong_mutate_mask, parents + noise, parents)
    mutated_parents.clamp_(0, 255)

    # cross over all chosen drones with the queen

    queen_parents = queen.unsqueeze(0).expand(POP_SIZE - 1, gene_length)
    queen_and_parents = torch.stack((queen_parents, mutated_parents), dim = 1)

    # in my experiments, the crossover point must be random between queen and drones for this to work
    # todo: get caught up with all the different types of crossover operators

    rand_crossover_order = torch.randn(queen_and_parents.shape[:2]).argsort(dim = -1)

    batch_arange = torch.arange(POP_SIZE - 1)[..., None]
    queen_and_parents = queen_and_parents[batch_arange, rand_crossover_order]
    queen_parents, mutated_parents = queen_and_parents.unbind(dim = 1)

    pool = torch.cat((queen_parents[:, :gene_midpoint], mutated_parents[:, gene_midpoint:]), dim = -1)

    # mutate genes in population

    mutate_mask = torch.randn(pool.shape).argsort(dim = -1) < num_code_mutate
    noise = torch.randint(0, 2, pool.shape) * 2 - 1
    mutated_pool = torch.where(mutate_mask, pool + noise, pool)

    pool.clamp_(0, 255)

    # increment generation

    generation += 1
