# %%
import pandas as pd

# %%
df = pd.read_excel("Itens - 2026-09-17T133257.920.xlsx")


# %%
df

# %%
carteira_exec = pd.read_excel("2026.09 - atualizado em 15.09.xlsx")

# %%
df = pd.merge(df, carteira_exec, how = 'left', right_on = 'ID Parceiro', left_on = 'Id Corretora')
df = df[df['Tipo Movimentação'] == 'VIDA NOVA']

# %%
df

# %%
df['Data Início Beneficiário'] = pd.to_datetime(df['Data Início Beneficiário'], errors='coerce',dayfirst=True)
df['Data Inclusão Vida'] = pd.to_datetime(df['Data Inclusão Vida'], errors='coerce',dayfirst=True)
df['Diferenca'] = (df['Data Inclusão Vida'] - df['Data Início Beneficiário']).dt.days

# %%
#Status_Beneficiario = 'Ativado'
#Status_Contrato = "Aprovado"
#Status_Vida = ['Ag.Ativação','Aposentado / Demitido','Ativo','Em Análise']
#df = df[(df['Descrição Status Atual Beneficiário'] == Status_Beneficiario) & (df['Descrição Status Atual Contrato'] == Status_Contrato) & (df['Descrição Status Vida'].isin(Status_Vida))]

descricao = ['SEM JUSTA CAUSA', 'JUSTA CAUSA', 'A PEDIDO DO BENEFICIÁRIO (RN561)', 'BENEFÍCIO DEMITIDO/APOSENTADO (RN279)', 'DESLIGAMENTO DA EMPRESA (RN279)', 'INADIMPLENTE',df['Descrição Cancelamento'].isnull()]
df = df[df['Descrição Cancelamento'].isin(descricao)]

# %%
df_nao_corretos = df[df['Diferenca'] > 0]
df_nao_corretos = df_nao_corretos[df_nao_corretos['Descrição Status Atual Beneficiário'] == 'Ativado']
df_nao_corretoss = df_nao_corretos[['Descrição Beneficiário', 'Data Início Beneficiário', 'Data Inclusão Vida', 'Diferenca']]
df_nao_corretoss

# %%
df_certo = df[df['Diferenca'] <= 0]
df_certo

# %%
df_certo['Data Inclusão Vida'] = pd.to_datetime(
    df_certo['Data Inclusão Vida'],
    dayfirst=True,
    errors='coerce'
)

df_certo['Competencia'] = df_certo['Data Inclusão Vida'].dt.strftime('%m/%Y')

df_certo['Data Inclusão Vida'] = df_certo['Data Inclusão Vida'].dt.strftime('%d/%m/%Y')

# %%
df_certo

# %%
ACOM = ['ODO','SEM']

df_saude = df_certo[~df_certo['Id Acomodação'].isin(ACOM)]



# %%
ACOM = ['ODO']
df_odonto = df_certo[df_certo['Id Acomodação'].isin(ACOM)]

# %%
df_saude

# %%
df_saude_agru_comp_analista = df_saude.groupby(['Competencia', 'NOME']).agg({'Id Corretora': 'count'}).reset_index()
df_saude_agru_comp_analista['Competencia'] = pd.to_datetime(df_saude_agru_comp_analista['Competencia'], format='%m/%Y', errors='coerce')
df_saude_agru_comp_analista=df_saude_agru_comp_analista[df_saude_agru_comp_analista['Competencia']>pd.to_datetime('2025-12-01')]
df_saude_agru_comp_analista

# %%
df_odonto_agru_comp_analista = df_odonto.groupby(['Competencia', 'NOME']).agg({'Id Corretora': 'count'}).reset_index()
df_odonto_agru_comp_analista['Competencia'] = pd.to_datetime(df_odonto_agru_comp_analista['Competencia'], format='%m/%Y', errors='coerce')
df_odonto_agru_comp_analista=df_odonto_agru_comp_analista[df_odonto_agru_comp_analista['Competencia']>pd.to_datetime('2025-12-01')]
df_odonto_agru_comp_analista

# %%
df_saude_group = df_saude.groupby('Competencia').agg({'Descrição Beneficiário': 'count'}).reset_index()


# %%

df_saude_group['Competencia'] = pd.to_datetime(df_saude_group['Competencia'], format='%m/%Y', errors='coerce')
df_saude_group=df_saude_group[df_saude_group['Competencia']>pd.to_datetime('2025-12-01')]
df_saude_group

# %%
df_odonto_group = df_odonto.groupby('Competencia').agg({'Descrição Beneficiário': 'count'}).reset_index()

df_odonto_group['Competencia'] = pd.to_datetime(df_odonto_group['Competencia'], format='%m/%Y', errors='coerce')
df_odonto_group=df_odonto_group[df_odonto_group['Competencia']>pd.to_datetime('2025-12-01')]
df_odonto_group


