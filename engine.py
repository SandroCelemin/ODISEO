import streamlit as st
from services.match import directional_match_want, directional_match_have
from services.utils import similarity
from collections import deque
from services.search import first_distance_items

max_depth = 100

def find_all_chains(algoritmo, intent, items, start_item_id):

    def transpose_graph(graph):
        
        transposed_graph = {item["item_id"]: [] for item in items}

        # Abans: (u_id: [v_id])
        for u_id, neighbours in graph.items():
            for neigbour in neighbours:
                v_id = neigbour["item_id"]
                transposed_graph[v_id].append(item_index[u_id])
                # Després: (v_id: [u_id])
                
        return transposed_graph
    
    
    # =====================================
    # ALGORISMES
    # =====================================
    def kosaraju(items_subset, original_graph):
        
        subgraph_ids = {item["item_id"] for item in items_subset}
        
        visited_ids = set()
        stack = deque([])
        
        # -----------------------------------
        # PRIMERA PASSADA DFS: Sobre el graf original
        # -----------------------------------
        def dfs_first_pass(current_item):
            
            visited_ids.add(current_item["item_id"])
            
            neighbours = original_graph.get(current_item["item_id"], [])
            
            for neighbour in neighbours:
                if neighbour["item_id"] in subgraph_ids and neighbour["item_id"] not in visited_ids:
                    dfs_first_pass(neighbour)
                    
            stack.append(current_item)
        
        for item in items_subset:
            if item["item_id"] not in visited_ids:
                dfs_first_pass(item)

        # --------------------------
        # Invertir el graf original
        # --------------------------
        transposed_graph = transpose_graph(original_graph)

        # ------------------------------------------------------------
        # SEGONA PASSADA DFS: En l'ordre de la pila sobre el graf invertit
        # ------------------------------------------------------------
        visited_ids.clear()
        sccs = []
        
        def dfs_second_pass(current_item, current_scc):
            
            visited_ids.add(current_item["item_id"])
            current_scc.append(current_item)
            
            neighbours = transposed_graph.get(current_item["item_id"], [])
            
            for neighbour in neighbours:
                if neighbour["item_id"] in subgraph_ids and neighbour["item_id"] not in visited_ids:
                    dfs_second_pass(neighbour, current_scc)
        
        while stack:
            item = stack.pop() # Equivalent a desapilar
            
            if item["item_id"] in subgraph_ids and item["item_id"] not in visited_ids:
                current_scc = []
                dfs_second_pass(item, current_scc)
                sccs.append(current_scc)
        
        return sccs
    """
    # Cerca els ITEMS ASSOLIBLES (no els camins per assolir-los) -> càrrega de marketplace
    def bfs(items_subset, intent, start_item):
        nonlocal results
        
        queue = deque([start_item["item_id"]])
        visited = {start_item["item_id"]}
        #visited.add(start_item["item_id"])
        
        results.append(start_item["item_id"])
        
        while queue:
            current_item_id = queue.popleft()
            neighbours = current_graph.get(current_item_id, []) # neighbours són ítems enters
            
            for neighbour in neighbours:
                if neighbour in items_subset and neighbour["user"] != item_index[current_item_id]["user"]:
                    if neighbour["item_id"] not in visited:
                        
                        #new_path = path + [neighbour["item_id"]]
                            
                        #queue.append(new_path)
                        queue.append(neighbour["item_id"])
                        visited.add(neighbour["item_id"])
                        results.append(neighbour["item_id"])
        
        # Ens quedem a results amb els ítems el user dels quals sigui diferent de l'usuari que està consultant el programa
        results = [
            item_index[item_id] for item_id in results 
            if item_index[item_id]["user"] != st.session_state.user
        ]
    """
    def bfs_modified(items_subset, intent, start_item):
        nonlocal results
        
        queue = deque([[start_item["item_id"]]])
        visited = [start_item["item_id"]]
        
        results.append([start_item["item_id"]])
        
        while queue:
            path = queue.popleft() # path és una llista on es guarda el camí de nodes que s'analitzarà a continuació al codi
            current_item_id = path[-1] # current_item_id és l'últim id de cada camí. Servirà per analitzar si s'ha arribat al node inicial
            visited = path # es posen com a visitats tots els ids NOMÉS del camí que s'està analitzant
            
            if len(path) > max_depth: # atura el BFS quan s'arriba al max_depth dels camins que està seguint
                print("ATURADA: profunditat màxima assolida")
                continue
                
            neighbours = current_graph.get(current_item_id, [])
            
            for neighbour in neighbours:
                # No es fa la comprovació "if neighbour in items_subset" perquè no es busquen cadenes reals sinó hipotètiques
                if neighbour["user"] != item_index[current_item_id]["user"]:
                    if neighbour["item_id"] not in visited:
                        
                        new_path = path + [neighbour["item_id"]]
                            
                        queue.append(new_path)
                        results.append(new_path)
        
        # Ens quedem a results amb els camins [Primer-->Segon-->Tercer...] el primer i l'últim ítem
        # dels quals no pertanyin a st.session_state.user perquè, en afegir el node fantasma,
        # no se li pugui donar ni rebre un objecte seu
        results = [
            path for path in results 
            if item_index[path[-1]]["user"] != st.session_state.user and item_index[path[0]]["user"] != st.session_state.user
        ]

    def dfs_modified(items_subset, intent, current_item, path, visited_ids):
        nonlocal cycles

        if len(path) > max_depth: # atura el DFS quan s'arriba al max_depth de la cadena
            print("ATURADA: profunditat màxima assolida")
            return
            
        item_intent = current_item[intent].strip() # item_intent és l'objecte (en forma de text) que hi ha dins del want o del have (depenent de l'intent)
        item_id = current_item["item_id"]
        
        if not item_intent:
            print("ATURADA: " + intent + " buit")
            return
            
        new_path = path + [item_id] #+ [item_intent] # afegim el want o el have (depèn de l'intent) actual
        results.append(new_path)
        
        neighbours = current_graph.get(item_id, [])
        
        for neighbour in neighbours:
            if neighbour in items_subset:
                if neighbour["user"] != current_item["user"]:
                    if neighbour["item_id"] == start_item_id and len(new_path) > 1:
                        cycles.append(new_path)
                        continue
                        
                    if neighbour["item_id"] not in visited_ids:
                        dfs_modified(items_subset, intent, neighbour, new_path, visited_ids | {neighbour["item_id"]})

    def johnson(find_all):
        nonlocal cycles
        
        pila = deque([])
        blocked_ids = set()
        B = {item["item_id"]: set() for item in items} # Al set() hi ha ids

        def unblock(u_id):
            blocked_ids.discard(u_id)
            
            if u_id in B:
                pending = list(B[u_id])
                B[u_id].clear()
                for w_id in pending:
                    if w_id in blocked_ids:
                        unblock(w_id)

        def find_cycles(current_id, start_id, A_K):
            f = False
            pila.append(current_id)
            blocked_ids.add(current_id)
            
            if len(pila) > max_depth:
                pila.pop()
                blocked_ids.discard(current_id)
                return False
            
            neighbours = A_K.get(current_id, [])
            
            for neighbour in neighbours:
                neigbour_id = neighbour["item_id"]

                if neigbour_id == start_id:
                    new_cycle = list(pila)
                    cycles.append(new_cycle)
                    f = True

                elif neigbour_id not in blocked_ids:
                    if find_cycles(neigbour_id, start_id, A_K):
                        f = True

            if f:
                unblock(current_id)
            else:
                for neighbour in neighbours:
                    neigbour_id = neighbour["item_id"]
                    if current_id not in B.setdefault(neigbour_id, set()):
                        B[neigbour_id].add(current_id)

            pila.pop()
            return f
        
        # --- BUCLE PRINCIPAL DE JOHNSON ---
        if find_all:
            # --- CERCA DE TOTS ELS CICLES ---
            s_idx = 0
            n = len(items_sorted)
            
            while s_idx < n:
                # Subgraf induït {s, s+1, ..., n} (llista d'ítems complets)
                subgraph_items = items_sorted[s_idx:]

                # 1. Trobar components fortament connectades (SCCs) amb Kosaraju
                sccs = kosaraju(subgraph_items, current_graph)

                # 2. Filtrar SCCs que formin cicles (no laços)
                valid_sccs = [scc for scc in sccs if len(scc) > 1]
                if not valid_sccs:
                    break

                # 3. Seleccionar la SCC que conté el vèrtex amb menor índex
                min_scc = min(
                    valid_sccs,
                    key=lambda scc: min(id_to_idx[item["item_id"]] for item in scc),
                )
                min_item = min(
                    min_scc, key=lambda item: id_to_idx[item["item_id"]]
                )
                s_item_id = min_item["item_id"]
                s_idx = id_to_idx[s_item_id]

                # 4. Estructura d'adjacència A_K restringida a min_scc
                scc_ids = {item["item_id"] for item in min_scc}
                A_K = {}
                for item in min_scc:
                    u_id = item["item_id"]
                    A_K[u_id] = [
                        nbr
                        for nbr in current_graph.get(u_id, [])
                        if nbr["item_id"] in scc_ids and nbr["user"] != item["user"] # Evita que un usuari intercanviï amb si mateix
                    ]

                # 5. Reinicialitzar estructures per a la SCC actual i buscar cicles
                for item in min_scc:
                    u_id = item["item_id"]
                    blocked_ids.discard(u_id)
                    B[u_id] = set()

                find_cycles(s_item_id, s_item_id, A_K)
                s_idx += 1
            
        else:
            # --- CERCA EXCLUSIVA PER A L'ÍTEM INICIAL ---
            if not items_subset:
                return cycles

            scc_ids = {item["item_id"] for item in items_subset}
            A_K = {}
            for item in items_subset:
                u_id = item["item_id"]
                A_K[u_id] = [
                    nbr
                    for nbr in current_graph.get(u_id, [])
                    if nbr["item_id"] in scc_ids and nbr["user"] != item["user"] 
                ]

            for item in items_subset:
                u_id = item["item_id"]
                blocked_ids.discard(u_id)
                B[u_id] = set()

            find_cycles(start_item_id, start_item_id, A_K)
            
        return cycles # Retorna una llista de ids
    
    
    # =====================================
    # INICIALITZACIÓ D'ESTRUCTURA
    # =====================================
    item_index = {item["item_id"]: item for item in items}
    
    if start_item_id not in item_index:
        return []
    
    items_sorted = sorted(items, key=lambda x: x["item_id"])
    id_to_idx = {
        item["item_id"]: idx for idx, item in enumerate(items_sorted)
    }

    graph_connexions_directional_match_have = {item["item_id"]: [] for item in items} # Graf original (Té --> Vol)
    graph_connexions_directional_match_want = {item["item_id"]: [] for item in items} # Graf transposat (Té <-- Vol)
    
    for current in items:
        for candidate in items:
            if current != candidate and current["user"] != candidate["user"]:
                if directional_match_have(current, candidate): 
                    
                    graph_connexions_directional_match_have[current["item_id"]].append(candidate)
                
                if directional_match_want(current, candidate): 
                    
                    graph_connexions_directional_match_want[current["item_id"]].append(candidate)

    # Segons l'intent current_graph serà el graf original o el transposat
    current_graph = (
        graph_connexions_directional_match_want
        if intent == "want"
        else graph_connexions_directional_match_have
    )

    results = []
    cycles = []

    start_item = item_index[start_item_id]
    
    # Busquem la SCC a la qual pertany 'start_item'
    sccs = kosaraju(items, current_graph)
    items_subset = None
    
    for scc in sccs:
        if start_item in scc:
            items_subset = scc
            break
    
    # items_subset és el conjunt d'ítems que forma la scc a la qual pertany el start item
    # (en bfs i dfs s'ha de comprovar a fora però en johnson es fa a dins (per això no surt com a condició aquí))
    if not items_subset and algoritmo in ["bfs", "bfs_modified", "dfs_modified"]:
        return []
    
    # =====================================
    # EXECUCIÓ DE L'ALGORISME SELECCIONAT
    # =====================================
    if algoritmo == "bfs":
        bfs(items_subset, intent, start_item)
        return results
        
    elif algoritmo == "bfs_modified":
        bfs_modified(items_subset, intent, start_item)
        return results
        
    elif algoritmo == "dfs_modified":
        dfs_modified(items_subset, intent, start_item, [], {start_item_id})
        return cycles        
        
    elif algoritmo == "kosaraju":
        return kosaraju(items, current_graph)
        
    elif algoritmo == "johnson_single":
        johnson(False)
        return cycles
        
    elif algoritmo == "johnson_all":
        johnson(True)
        return cycles


def get_items_from_have_chains(items, have_text, intent): # S'executa quan intent és have
    """
    seeds = first_distance_items(items, have_text, intent)
    chains = []
    
    for seed in seeds:

        chains_from_seed = find_all_chains("bfs_modified", intent, items, seed["item_id"])
        
        for chain in chains_from_seed:
            chains.append(chain)
            
    visited_items = set()
    results = []
    
    item_dict = {x["item_id"]: x for x in items}
    
    for chain in chains:
        for item_id in chain:
            if item_id not in visited_items:
                
                item = item_dict[item_id]
                
                results.append(item)
                visited_items.add(item_id)
    
    return results # És una llista d'ítems
    """
    #===================
    # MATRIU ADJACÈNCIA
    #===================
    graph_connexions_directional_match_have = {item["item_id"]: [] for item in items} # Graf original (Té --> Vol)
    graph_connexions_directional_match_want = {item["item_id"]: [] for item in items} # Graf transposat (Té <-- Vol)
    
    for current in items:
        for candidate in items:
            if current != candidate and current["user"] != candidate["user"]:
                if directional_match_have(current, candidate): 
                    
                    graph_connexions_directional_match_have[current["item_id"]].append(candidate)
                
                if directional_match_want(current, candidate): 
                    
                    graph_connexions_directional_match_want[current["item_id"]].append(candidate)

    # Segons l'intent current_graph serà el graf original o el transposat
    current_graph = (
        graph_connexions_directional_match_want
        if intent == "want"
        else graph_connexions_directional_match_have
    )
    
    item_index = {x["item_id"]: x for x in items}
    
    #=================
    # ALGORISME BFS
    #=================
    
    # Cerca els ÍTEMS ASSOLIBLES (no els camins per assolir-los) -> càrrega de marketplace
    def bfs(intent, start_seeds):
        
        results = []
        queue = deque(start_seeds)
        visited = set(start_seeds)
        
        results.extend(start_seeds)
        
        while queue:
            current_item_id = queue.popleft()
            neighbours = current_graph.get(current_item_id, []) # neighbours són ítems enters
            
            for neighbour in neighbours:
                if neighbour["user"] != item_index[current_item_id]["user"]:
                    if neighbour["item_id"] not in visited:
                        
                        #new_path = path + [neighbour["item_id"]]
                            
                        #queue.append(new_path)
                        queue.append(neighbour["item_id"])
                        visited.add(neighbour["item_id"])
                        results.append(neighbour["item_id"])
        
        # Ens quedem a results amb els ítems el user dels quals sigui diferent de l'usuari que està consultant el programa
        results = [
            item_index[item_id] for item_id in results 
            if item_index[item_id]["user"] != st.session_state.user
        ]
        
        return results

    #======================
    # ESTRUCTURA PRINCIPAL
    #======================
    seeds = first_distance_items(items, have_text, intent)
    reachable_items = []
    visited_ids = set()
    
    seeds_ids = deque([seed["item_id"] for seed in seeds])
    reachable_items = bfs(intent, seeds_ids)
    
    #return reachable_items # És una llista d'ítems
    return reachable_items
    #"""
"""
------ BFS ABANS DE LA LLISTA D'ADJACÈNCIA ------
   
   def bfs(intent, start_item):
        
        cola = deque([[start_item]])
        visited = [start_item]
        
        results.append([start_item])
        
        while cola:
            camino = cola.popleft() # camino és una llista on es guarda el camí de nodes que s'analitzen actualment
            current_item = camino[-1] # nodo és l'últim ítem de cada camí. Servirà per analitzar si s'ha arribat al node inicial
            visited = camino
            
            if len(camino) > max_depth: # atura el BFS quan s'arriba al max_depth dels camins que està seguint
                print("ATURADA: profunditat màxima assolida")
                return
            
            for vecino in items:
                if vecino not in visited:
                    #visited.add(vecino["item_id"])
                    
                    if intent == "want": match = directional_match_want(current_item, vecino)
                    if intent == "have": match = directional_match_have(current_item, vecino)
                    
                    if match:
                        #visited.add(vecino["item_id"])
                        
                        nuevo_camino = camino + [vecino]
                        
                        cola.append(nuevo_camino)
                        results.append(nuevo_camino)


------ BFS DESPRÉS DE LA LLISTA D'ADJACÈNCIA ------

    def bfs(intent, start_item):
        
        queue = deque([[start_item["item_id"]]])
        visited = [start_item["item_id"]]
        
        results.append([start_item["item_id"]])
        
        while queue:
            path = queue.popleft() # path és una llista on es guarda el camí de nodes que s'analitzarà a continuació al codi
            current_item_id = path[-1] # current_item_id és l'últim id de cada camí. Servirà per analitzar si s'ha arribat al node inicial
            visited = path # es posen com a visitats tots els ids NOMÉS del camí que s'està analitzant
            
            if len(path) > max_depth: # atura el BFS quan s'arriba al max_depth dels camins que està seguint
                print("ATURADA: profunditat màxima assolida")
                continue
            
            if intent == "want": 
                neighbours = graph_connexions_directional_match_want.get(current_item_id, [])
            if intent == "have": 
                neighbours = graph_connexions_directional_match_have.get(current_item_id, [])
            
            for neighbour in neighbours:
                if neighbour["item_id"] not in visited:
                    
                    new_path = path + [neighbour["item_id"]]
                        
                    queue.append(new_path)
                    results.append(new_path)


---- PRIMERA VERSIÓ DFS DETECCIÓ DE CICLES -----

    def dfs(intent, current_item, path, visited_ids):

        if len(path) > max_depth: # atura el DFS quan s'arriba al max_depth de la cadena
            print("ATURADA: profunditat màxima assolida")
            return

        item_intent = current_item[intent].strip() # item_intent és l'objecte (en forma de text) que hi ha dins del want o del have (depenent de l'intent)
        item_id = current_item["item_id"]
        
        if not item_intent:
            print("ATURADA: " + intent + " buit")
            return

        new_path = path + [item_id] #+ [item_intent] # afegim el want o el have (depèn de l'intent) actual
        
        results.append(new_path)

        for item in items: # RECURRÈNCIA; buscar TOTS els següents (no només un)

            if item["item_id"] in visited_ids:
                
                if item["item_id"] == start_item_id:
                    
                    if intent == "want": match = directional_match_want(current_item, item)
                    if intent == "have": match = directional_match_have(current_item, item)
                    
                    if match:
                        cyclic_chain = new_path #+ [item["item_id"]]
                        cycles.append(cyclic_chain)
                    #new_path = path + [item_id] + [item_intent]
                continue

            if intent == "want": match = directional_match_want(current_item, item)
            if intent == "have": match = directional_match_have(current_item, item)
            
            if match:
                dfs(intent, item, new_path, visited_ids | {item["item_id"]})
                
                
------ SEGONA VERSIÓ DFS DETECCIÓ DE CICLES
    
    def dfs(intent, current_item, path, visited_ids):

        if len(path) > max_depth: # atura el DFS quan s'arriba al max_depth de la cadena
            print("ATURADA: profunditat màxima assolida")
            return

        item_intent = current_item[intent].strip() # item_intent és l'objecte (en forma de text) que hi ha dins del want o del have (depenent de l'intent)
        item_id = current_item["item_id"]
        
        if not item_intent:
            print("ATURADA: " + intent + " buit")
            return

        new_path = path + [item_id] #+ [item_intent] # afegim el want o el have (depèn de l'intent) actual
        
        results.append(new_path)

        for item in items: # RECURRÈNCIA; buscar TOTS els següents (no només un)

            # Comprova en cada iteració si hi ha match amb l'objecte d'inici i (si n'hi ha) guarda aquest recorregut com una cadena
            # sense incloure el primer objecte al final de la llista (i.e. A -> B -> C ( -> A)) 
            #                                                                   ^^^^^^^ {l'últim A no es guarda}
            if intent == "want": match = directional_match_want(current_item, start_item)
            if intent == "have": match = directional_match_have(current_item, start_item)
            
            if match
                cycles.append(new_path)

                continue
            
            if intent == "want": match = directional_match_want(current_item, item)
            if intent == "have": match = directional_match_have(current_item, item)
            
            if match:
                dfs(intent, item, new_path, visited_ids | {item["item_id"]})
"""