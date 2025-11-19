import matplotlib.pyplot as plt
import numpy as np
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def processar_arquivo(caminho):
    """Processa o arquivo de log e retorna os dados necessários."""
    try:
        arq = open(caminho, "r")
    except:
        messagebox.showerror("Erro", "Caminho para o arquivo não existe ou não pode ser aberto.")
        return None

def processar_arquivo(caminho):
    """Processa o arquivo de log e retorna os dados necessários."""
    try:
        arq = open(caminho, "r")
    except:
        messagebox.showerror("Erro", "Caminho para o arquivo não existe ou não pode ser aberto.")
        return None

    num_expansoes = {}
    f = {}
    g = {}
    h = {}
    saltos = []
    num_saltos = 0
    iteracao = []
    med_h_vizinhos = {}

    # Pula as primeiras linhas de cabeçalho
    linha = arq.readline()  # Linha 1: PA-Star Execution Log
    linha = arq.readline()  # Linha 2: Threads: X
    linha = arq.readline()  # Linha 3: Hash: ...
    linha = arq.readline()  # Linha 4: Shift: ...
    linha = arq.readline()  # Linha 5: linha vazia
    linha = arq.readline()  # Linha 6: primeira linha de dados

    # Pula linhas vazias até encontrar dados
    while linha.strip() == "":
        linha = arq.readline()
        if not linha:
            messagebox.showerror("Erro", "Arquivo não contém dados de execução.")
            arq.close()
            return None

    linha = linha.split("\t")

    # Determinacao da quantidade de dimensoes dos vertices:
    dimensoes = len(linha[3].strip().replace("(", "").replace(")", "").split())

    # Inicio da varredura dos vertices.
    while linha and linha[0].strip() and (linha[0][0] != "P"):
        coordenada_str = linha[3].strip()
        no = coordenada_str.replace("(", "").replace(")", "").split()
        for i in range(len(no)):
            no[i] = int(no[i])

        no = tuple(no)
        iteracao.append((int(linha[1]), no))

        # Registros de f, g e h
        valores_str = linha[4].strip()
        
        # Detectar formato: verifica se contém "g(" ou "g -"
        if "g(" in valores_str:
            # Formato novo: g(90) h(82) f(172)
            valores = valores_str.split()
            g_str = valores[0].replace("g(", "").replace(")", "")
            h_str = valores[1].replace("h(", "").replace(")", "")
            f_str = valores[2].replace("f(", "").replace(")", "")
        else:
            # Formato antigo: g - 90 (h - 82 f - 172)
            # Remove parênteses e faz split
            valores_str = valores_str.replace("(", "").replace(")", "")
            partes = valores_str.split()
            # Formato: g - 90 h - 82 f - 172
            g_str = partes[2]  # posição após "g -"
            h_str = partes[5]  # posição após "h -"
            f_str = partes[8]  # posição após "f -"

        g[no] = int(g_str)
        h[no] = int(h_str)
        f[no] = int(f_str)

        linha = arq.readline()
        if linha:
            linha = linha.split("\t")

    arq.close()

    # Ordenacao da lista de iteracoes
    iteracao.sort()

    return {
        'num_expansoes': num_expansoes,
        'f': f,
        'g': g,
        'h': h,
        'saltos': saltos,
        'num_saltos': num_saltos,
        'iteracao': iteracao,
        'med_h_vizinhos': med_h_vizinhos,
        'dimensoes': dimensoes
    }


def get_vizinhos(vertice, lista_viz, indice):
    """Retorna os vizinhos de um vertice."""
    if indice <= 0:
        lista_viz.append(vertice)
        novo_vertice = list(vertice)
        novo_vertice[indice] += 1
        lista_viz.append(tuple(novo_vertice))
        if novo_vertice[indice] > 1:
            novo_vertice[indice] -= 2
            lista_viz.append(tuple(novo_vertice))
        return lista_viz

    lista_viz.append(vertice)
    lista_viz = get_vizinhos(vertice, lista_viz.copy(), indice - 1)
    novo_vertice = list(vertice)
    novo_vertice[indice] += 1
    lista_viz = get_vizinhos(tuple(novo_vertice), lista_viz.copy(), indice - 1)
    if novo_vertice[indice] > 1:
        novo_vertice[indice] -= 2
        lista_viz = get_vizinhos(tuple(novo_vertice), lista_viz.copy(), indice - 1)
    return lista_viz


def calcular_metricas(dados):
    """Calcula as métricas adicionais dos dados processados."""
    num_expansoes = dados['num_expansoes']
    h = dados['h']
    iteracao = dados['iteracao']
    saltos = dados['saltos']
    med_h_vizinhos = dados['med_h_vizinhos']
    dimensoes = dados['dimensoes']
    
    indice = dimensoes - 1
    no_anterior = None
    num_saltos = 0

    for it in iteracao:
        vertice = it[1]
        try:
            num_expansoes[vertice] += 1
        except:
            num_expansoes[vertice] = 1

        vizinhos = get_vizinhos(vertice, [], indice)
        vizinhos = list(dict.fromkeys(vizinhos))
        vizinhos.remove(vertice)

        if no_anterior != None:
            if not (no_anterior in vizinhos):
                num_saltos += 1
                saltos.append((no_anterior, vertice))

        num_viz = 0
        soma = 0
        for vizinho in vizinhos:
            try:
                soma += h[vizinho]
            except:
                continue
            num_viz += 1

        if num_viz == 0:
            med_h_vizinhos[vertice] = -1
        else:
            med_h_vizinhos[vertice] = soma / num_viz

        no_anterior = vertice
    
    dados['num_saltos'] = num_saltos
    return dados


def gerar_grafico(dados):
    """Gera o gráfico de visualização."""
    iteracao = dados['iteracao']
    dimensoes = dados['dimensoes']
    
    if dimensoes > 3:
        messagebox.showinfo("Atenção", f"O arquivo possui {dimensoes} dimensões. Apenas gráficos 3D (3 dimensões) são suportados.")
        return None
    
    x = []
    y = []
    z = []
    tempo = []
    
    for it in iteracao:
        x.append(it[1][0])
        y.append(it[1][1])
        z.append(it[1][2])
        tempo.append(it[0])

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    grafico = ax.scatter(x, y, z, c=tempo, cmap='viridis', marker='o')
    ax.set_xlabel("Sequência 1")
    ax.set_ylabel("Sequência 2")
    ax.set_zlabel("Sequência 3")

    barra = fig.colorbar(grafico)
    barra.set_label('Iteração')
    
    return fig


class PAStarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PA-Star Runtime Visualizer")
        self.root.geometry("1000x700")
        
        self.dados = None
        self.figura_atual = None
        
        # Frame principal
        frame_botoes = tk.Frame(root)
        frame_botoes.pack(pady=10)
        
        # Botão para abrir arquivo
        self.btn_abrir = tk.Button(frame_botoes, text="Abrir Arquivo Log", 
                                    command=self.abrir_arquivo, 
                                    font=("Arial", 12), 
                                    bg="#4CAF50", 
                                    fg="white",
                                    padx=20, pady=10)
        self.btn_abrir.pack(side=tk.LEFT, padx=5)
        
        # Botão para salvar imagem
        self.btn_salvar = tk.Button(frame_botoes, text="Salvar Imagem", 
                                     command=self.salvar_imagem, 
                                     font=("Arial", 12),
                                     bg="#2196F3",
                                     fg="white",
                                     padx=20, pady=10,
                                     state=tk.DISABLED)
        self.btn_salvar.pack(side=tk.LEFT, padx=5)
        
        # Label de status
        self.label_status = tk.Label(root, text="Aguardando arquivo...", 
                                      font=("Arial", 10))
        self.label_status.pack(pady=5)
        
        # Frame para o gráfico
        self.frame_grafico = tk.Frame(root)
        self.frame_grafico.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def abrir_arquivo(self):
        """Abre o arquivo de log e processa os dados."""
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo de log",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        
        if not caminho:
            return
        
        self.label_status.config(text="Processando arquivo...")
        self.root.update()
        
        # Processa o arquivo
        dados = processar_arquivo(caminho)
        if dados is None:
            self.label_status.config(text="Erro ao processar arquivo")
            return
        
        # Calcula métricas
        dados = calcular_metricas(dados)
        self.dados = dados
        
        # Gera o gráfico
        fig = gerar_grafico(dados)
        if fig is None:
            self.label_status.config(text="Erro ao gerar gráfico")
            return
        
        self.figura_atual = fig
        
        # Limpa o frame de gráfico anterior
        for widget in self.frame_grafico.winfo_children():
            widget.destroy()
        
        # Mostra o gráfico na GUI
        canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Habilita o botão de salvar
        self.btn_salvar.config(state=tk.NORMAL)
        
        # Atualiza status
        num_iteracoes = len(dados['iteracao'])
        num_saltos = dados['num_saltos']
        self.label_status.config(
            text=f"Arquivo processado! Iterações: {num_iteracoes} | Saltos: {num_saltos}"
        )
    
    def salvar_imagem(self):
        """Salva a imagem do gráfico."""
        if self.figura_atual is None:
            messagebox.showwarning("Aviso", "Nenhum gráfico para salvar!")
            return
        
        caminho = filedialog.asksaveasfilename(
            title="Salvar imagem como",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not caminho:
            return
        
        try:
            self.figura_atual.savefig(caminho, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Sucesso", f"Imagem salva em:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar imagem:\n{str(e)}")


def main():
    root = tk.Tk()
    app = PAStarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
