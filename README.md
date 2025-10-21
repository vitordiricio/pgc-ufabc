# Simulação para Otimização de Tráfego Urbano

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Projeto de Graduação em Computação - Universidade Federal do ABC (UFABC)**

</div>

## 📋 Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Heurísticas Implementadas](#heurísticas-implementadas)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Instalação](#instalação)
- [Uso](#uso)
- [Análise de Métricas](#análise-de-métricas)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Contribuições](#contribuições)

## 👥 Autores

- **Vitor Bobig Diricio**
- **Thiago Schwartz Machado**

## 🎯 Sobre o Projeto

Este projeto implementa uma simulação avançada de tráfego urbano com foco na otimização através de diferentes estratégias de controle de semáforos. O sistema permite a comparação entre múltiplas heurísticas de controle, possibilitando a análise detalhada do impacto de cada estratégia no fluxo de veículos.

### Objetivos Principais

1. **Análise Comparativa**: Avaliar diferentes heurísticas de controle de semáforos
2. **Otimização de Fluxo**: Identificar estratégias que minimizem congestionamentos
3. **Métricas de Desempenho**: Coletar e analisar dados detalhados sobre o tráfego
4. **Visualização em Tempo Real**: Observar o comportamento do sistema dinamicamente

## 🚀 Funcionalidades

### Sistema de Simulação

- **Malha Viária Escalável**: Suporte para grades de múltiplos cruzamentos (configurável)
- **Física Realista**: Implementação de aceleração, frenagem e comportamento veicular natural
- **Detecção de Colisão**: Sistema robusto para evitar sobreposições entre veículos
- **Spawn Inteligente**: Geração de veículos em múltiplos pontos com controle de densidade

### Controle de Semáforos

- **Múltiplas Heurísticas**: 4 estratégias diferentes de controle implementadas
- **Sincronização**: Semáforos coordenados para evitar conflitos
- **Adaptabilidade**: Ajuste dinâmico baseado em condições de tráfego

### Interface e Visualização

- **Interface Moderna**: Design limpo e informativo
- **Estatísticas em Tempo Real**: Métricas atualizadas continuamente
- **Controles Intuitivos**: Comandos simples para interação com a simulação
- **Mensagens de Feedback**: Informações claras sobre o estado do sistema

### Análise de Dados

- **Coleta Automática**: Métricas registradas durante a simulação
- **Exportação de Relatórios**: Dados salvos em formato JSON
- **Análise Comparativa**: Ferramenta dedicada para comparar heurísticas
- **Visualização de Resultados**: Gráficos e tabelas comparativas

## 🧠 Heurísticas Implementadas

### 1. Tempo Fixo

- **Descrição**: Semáforos alternam em intervalos predefinidos
- **Vantagem**: Simplicidade e previsibilidade
- **Desvantagem**: Não se adapta ao fluxo real

### 2. Adaptativa Simples

- **Descrição**: Ajusta tempos baseado na densidade relativa entre direções
- **Vantagem**: Responde a variações básicas de tráfego
- **Desvantagem**: Análise limitada das condições

### 3. Adaptativa por Densidade

- **Descrição**: Análise detalhada da densidade com múltiplos limiares
- **Vantagem**: Resposta mais precisa às condições de tráfego
- **Desvantagem**: Maior complexidade computacional

### 4. Onda Verde (Wave Green)

- **Descrição**: Sincronização progressiva para criar fluxo contínuo
- **Vantagem**: Otimiza o fluxo em vias principais
- **Desvantagem**: Pode penalizar vias secundárias

### 5. ChatGPT (OpenAI)

- **Descrição**: Consulta um modelo de linguagem (ChatGPT) para sugerir a fase ótima do semáforo
- **Vantagem**: Analisa o estado global usando heurísticas aprendidas
- **Desvantagem**: Requer chave de API da OpenAI e conexão com a internet

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Configuração  │────▶│    Simulação     │────▶│  Renderizador   │
│  (CONFIG)       │     │   (Principal)    │     │   (Visual)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Malha Viária   │────▶│   Cruzamentos    │────▶│    Veículos     │
│   (Grid)        │     │  (Intersections) │     │   (Agents)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Semáforos     │────▶│   Heurísticas    │────▶│    Métricas     │
│  (Control)      │     │  (Strategies)    │     │   (Analysis)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 💻 Instalação

### Requisitos do Sistema

- Python 3.8 ou superior
- Sistema operacional: Windows, macOS ou Linux

### Instalação Básica

1. **Clone o repositório**:

```bash
git clone https://github.com/seu-usuario/simulacao-trafego-urbano.git
cd simulacao-trafego-urbano
```

2. **Crie um ambiente virtual** (recomendado):

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências essenciais**:

```bash
pip install pygame
```

### Instalação Completa (com análise de métricas)

```bash
pip install -r requirements.txt
```

## 🎮 Uso

### Execução Básica

```bash
python main.py
```

### Heurística ChatGPT com GUI

Para executar a heurística baseada no ChatGPT com interface gráfica, é necessário definir as credenciais do serviço da OpenAI. Você pode usar variáveis de ambiente ou passar as credenciais diretamente na linha de comando.

> ⚠️ **Atenção no Windows (PowerShell):** o formato `OPENAI_API_KEY=valor comando` não é reconhecido. Utilize `$env:VARIAVEL = 'valor'` ou as flags `--openai-api-key`/`--openai-model` demonstradas abaixo.

#### Usando variáveis de ambiente

- **Linux/macOS (bash/zsh)**

    ```bash
    OPENAI_API_KEY='<seu_token>' OPENAI_MODEL='gpt-5-mini' python main.py --chatgpt --gui
    ```

- **Windows PowerShell**

    ```powershell
    $env:OPENAI_API_KEY = '<seu_token>'
    $env:OPENAI_MODEL = 'gpt-5-mini'
    python main.py --chatgpt --gui
    ```

- **Windows Prompt de Comando (CMD)**

    ```cmd
    set OPENAI_API_KEY=<seu_token>
    set OPENAI_MODEL=gpt-5-mini
    python main.py --chatgpt --gui
    ```

    > 💡 O terminal embutido do IntelliJ IDEA usa o Prompt de Comando por padrão. Execute os três comandos acima na mesma sessão para garantir que as variáveis `OPENAI_API_KEY` e `OPENAI_MODEL` sejam reconhecidas antes de iniciar o `python main.py`.

    ```cmd
    REM Versão em linha única usando o Prompt de Comando
    set OPENAI_API_KEY=<seu_token> && set OPENAI_MODEL=gpt-5-mini && python main.py --chatgpt --gui
    ```

    > ✅ Útil no terminal do IntelliJ/CLion: copie e cole a linha acima substituindo `<seu_token>` e pressione **Enter** para definir as variáveis e iniciar a simulação de uma só vez.

#### Passando credenciais pela linha de comando

```bash
python main.py --chatgpt --gui --openai-api-key "<seu_token>" --openai-model gpt-5-mini
```

Substitua `<seu_token>` pela sua chave real da OpenAI. Caso o modelo não seja especificado (por variável de ambiente ou flag), `gpt-5-mini` será utilizado por padrão.

### Controles da Simulação

| Tecla    | Ação                                 |
| -------- | ------------------------------------ |
| `ESPAÇO` | Pausar/Continuar simulação           |
| `1`      | Heurística: Tempo Fixo               |
| `2`      | Heurística: Adaptativa Simples       |
| `3`      | Heurística: Adaptativa por Densidade |
| `4`      | Heurística: Onda Verde               |
| `+`/`-`  | Aumentar/Diminuir velocidade         |
| `R`      | Reiniciar simulação                  |
| `TAB`    | Alternar exibição de estatísticas    |
| `CTRL+S` | Salvar relatório de métricas         |
| `ESC`    | Sair da simulação                    |

### Configurações Personalizadas

Edite o arquivo `configuracao.py` para ajustar:

```python
# Tamanho da grade
LINHAS_GRADE = 3
COLUNAS_GRADE = 4

# Taxa de geração de veículos
TAXA_GERACAO_VEICULO = 0.015

# Heurística inicial
HEURISTICA_ATIVA = TipoHeuristica.ADAPTATIVA_DENSIDADE
```

## 📊 Análise de Métricas

### Executar Análise

Após executar algumas simulações:

```bash
python analisador_metricas.py
```

### Métricas Coletadas

- **Tempo de Viagem**: Tempo total do veículo no sistema
- **Tempo Parado**: Tempo aguardando em semáforos
- **Eficiência**: Percentual de tempo em movimento
- **Densidade**: Número de veículos por cruzamento
- **Taxa de Fluxo**: Veículos processados por unidade de tempo

### Saídas da Análise

1. **Tabela Comparativa**: Resumo estatístico no console
2. **Gráficos**: Visualização comparativa (requer matplotlib)
3. **Relatório JSON**: Dados completos para análise posterior

## 📁 Estrutura do Projeto

```
simulacao-trafego-urbano/
│
├── main.py                 # Ponto de entrada principal
├── configuracao.py         # Configurações e constantes
├── simulacao.py           # Lógica principal da simulação
├── cruzamento.py          # Gerenciamento de cruzamentos e malha
├── veiculo.py             # Comportamento dos veículos
├── semaforo.py            # Controle de semáforos e heurísticas
├── renderizador.py        # Sistema de visualização
├── analisador_metricas.py # Análise de dados coletados
│
├── relatorios/            # Diretório para relatórios gerados
├── requirements.txt       # Dependências do projeto
├── README.md             # Documentação
└── .gitignore            # Arquivos ignorados pelo Git
```

## 🔧 Desenvolvimento

### Adicionar Nova Heurística

1. Adicione o tipo em `configuracao.py`:

```python
class TipoHeuristica(Enum):
    MINHA_HEURISTICA = auto()
```

2. Implemente a lógica em `semaforo.py`:

```python
def _atualizar_minha_heuristica(self, densidade):
    # Sua lógica aqui
    pass
```

3. Adicione ao switch de heurísticas no `GerenciadorSemaforos`

### Testes

Para executar testes (se implementados):

```bash
pytest tests/
```

## 🤝 Contribuições

Este projeto foi desenvolvido como trabalho de conclusão de curso. Para sugestões ou melhorias:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙏 Agradecimentos

- **Universidade Federal do ABC** - Pelo suporte acadêmico
- **Orientadores** - Pela orientação durante o desenvolvimento
- **Comunidade Python/Pygame** - Pelos recursos e documentação

---

<div align="center">
Desenvolvido com ❤️ para o PGC - UFABC
</div>
