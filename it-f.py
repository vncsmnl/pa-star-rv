import matplotlib.pyplot as plt
import sys

num_threads = ["1", "2", "4", "8"]
subplots = [221, 222, 223, 224]
titles = ["1 Thread", "2 Threads", "4 Threads", "8 Threads"]
minMax = (len(sys.argv) == 4) # Verifica se foram fornecidos valores de minimo e maximo na linha de comando
if minMax:
        try:
            y_min = int(sys.argv[2])
            y_max = int(sys.argv[3])
        except:
            print("Coloque um numero inteiro como limite minimo e/ou maximo")
            quit()

for num in range(4):
    # Escolha do arquivo a ser aberto.
    try:
        caminho = sys.argv[1] + "/log" + num_threads[num] + ".txt"
        arq = open(caminho, "r")
    except:
        print(f"Erro: caminho para o diretorio nao existe ou nao foi digitado.")
        quit()

    num_expansoes = {} # Guardara o numero de expansoes de cada vertice
    # Guardarao os valores de F, G e H de cada vertice
    f = {}
    g = {}
    h = {}
    iteracao = [] # Lista de iteracoes. Cada iteracao eh uma tupla que contem o numero da iteracao e o no que foi expandido nela.


    # Os arquivos de log mostram os dados da varredura a partir da sexta linha.
    # Assim, as primeiras cinco linhas (incluindo a linha vazia) sao descartadas.

    linha = arq.readline()
    linha = arq.readline()
    linha = arq.readline()
    linha = arq.readline()
    linha = arq.readline()
    linha = arq.readline() # A sexta linha do log fica guardada (primeira linha de dados)

    # Cada linha tem os seguintes dados, separados por tabulacoes:
    #   0.  numero da thread
    #   1.  numero da iteracao
    #   2.  a expressao "Adding:"
    #   3.  coordenada do vertice adicionado
    #   4.  valor de g, h e f
    linha = linha.split("\t")

    # Inicio da varredura dos vertices.
    # A primeira linha após o relatorio com os nos comeca com "Phase 2". Assim, quando
    # se detecta que o primeiro caracter da linha é "P", a varredura e encerrada.
    dimensoes = None
    while (len(linha) >= 5 and linha[0][0] != "P"):
        # Determinacao da quantidade de dimensoes dos vertices (na primeira iteracao):
        if dimensoes is None:
            dimensoes = len(linha[3].split(" "))
        
        # Pega a coordenada da linha e armazena no vetor de vertices
        no = linha[3].replace("(", "").replace(")","").split(" ")
        for i in range(len(no)):
            no[i] = int(no[i])

        no = tuple(no)

        # Registra a iteracao na lista de iteracoes e o vertice correspondente na lista de iteracoes.
        iteracao.append((int(linha[1]), no))

        # Registros de f, g e h
        # linha[4] tem o formato: "g(90) h(6913) f(7003)\n"
        proximos = linha[4].strip().replace(")", "").replace("(", " ").split()
        # proximos agora é: ['g', '90', 'h', '6913', 'f', '7003']
        g[no] = int(proximos[1])
        h[no] = int(proximos[3])
        f[no] = int(proximos[5])

        # Le a proxima linha
        linha = arq.readline().split("\t")

    arq.close()

    # Ordenacao da lista de iteracoes
    iteracao.sort()

    # Geracao dos graficos

    num_interacao = []
    valor_f = []
    valor_g = []
    valor_h = []
    for it in iteracao:
        num_interacao.append(it[0])
        valor_f.append(f[it[1]])
        valor_h.append(h[it[1]])
        valor_g.append(g[it[1]])

    ax = plt.subplot(subplots[num])
    if minMax:    
        plt.ylim(y_min, y_max)
    ax.set_title(titles[num])
    ax.plot(num_interacao, valor_f, 'y-')
    ax.set_xlabel("Iteração")
    ax.set_ylabel("Valor de f")

plt.show()