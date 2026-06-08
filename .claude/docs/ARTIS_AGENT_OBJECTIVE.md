Briefing Técnico — Rig SKEL_Char_Master para Unreal Engine 5
Destinatário: artista 3D (via blender-agent ou direto)
Projeto: Buteco (UE 5.7)
Arquivo de origem: .blend do personagem Manuel (rig + mesh + animações)
Arquivos de destino: FBX importáveis no UE5 sem ajustes manuais

1. PROBLEMA ATUAL (o que veio do .blend que tá quebrado)
Inspecionei o skeleton importado (SKEL_Char_Master) via Python no UE editor. Estes são os problemas concretos:

1.1. Forward axis errado
Atual: forward_axis = Y (convenção Blender padrão)
Esperado UE5: forward_axis = X (convenção Unreal Mannequin)
Sintoma: todo skeletal control que usa rotação aditiva (Modify Bone, AimOffset cru, IK) opera nos eixos errados. Cabeça vira lateral quando deveria virar pra cima, etc.
1.2. Bones com Roll ≠ 0 (rolled axes)
Valores reais que medi no ComponentSpace (T-pose):

Bone	Roll (graus)	Eixo Y local aponta pra	Eixo Z local aponta pra
spine_01	77.9°	-Z componente (baixo)	+Y (lateral)
spine_02	81.8°	-Z (baixo)	+Y (lateral)
neck_01	104.5°	-Z (baixo)	+Y (lateral)
head_01	90.4°	-Z (baixo)	+Y (lateral)
head_01_end	90.4°	-Z (baixo)	+Y (lateral)
Convenção UE5 esperada (Mannequin): todo bone da spine/neck/head deve ter:

Eixo X local apontando do bone pro filho (cadeia da coluna)
Eixo Z local apontando pra trás (back of head) ou pra cima
Eixo Y local apontando lateral (right)
Roll = 0 ou múltiplo de 90 INTENCIONAL e consistente.
1.3. Falta de poses de AimOffset
O .blend entrega só:

Bind pose (T-pose ou A-pose)
Animações de locomoção (Idle, Walk, Run — provavelmente)
O que falta: 9 poses de Aim (cabeça + tronco olhando em 9 direções) pra criar o sistema de "olhar pra onde a câmera aponta" estilo PEAK/Lyra/ALS.

2. O QUE PRECISAMOS QUE VOLTE DO ARTISTA
2.1. Reorientação do skeleton (rig hygiene)
Antes de qualquer animação nova, o skeleton precisa ser saneado:

a) Definir bone roll = 0 (ou alinhado com convenção UE) em toda a cadeia da coluna/cabeça:

spine_01, spine_02, spine_03 (se existir)
neck_01, neck_02 (se existir)
head_01
Como fazer no Blender:

Edit Mode no Armature
Selecionar bone
N panel → Item → Roll → 0
OU Armature menu → Bone Roll → Clear Roll
Verificar com Viewport Overlays → Axes ativado: o eixo verde (Y local do Blender = direção do bone) deve apontar do head pro tail. O eixo azul (Z local Blender = "up" do bone) deve apontar para TRÁS do personagem (back/spine direction).
⚠️ Não trocar de um bone individual sem garantir que a malha continua weighted corretamente. Pode precisar Recalculate Roll → Global Z Axis (Ctrl+N) com bones selecionados em Edit Mode, e depois aplicar Pose Mode → Apply → Visual Transform.

b) Adicionar IK_Foot_Root, IK_Foot_L, IK_Foot_R, IK_Hand_Root, IK_Hand_Gun, IK_Hand_L, IK_Hand_R (opcional mas padrão UE):

Não influenciam pesos, mas o UE detecta como IK targets em retargeting.
Posicionar IK_Foot_Root em (0, 0, 0) (na origem do mesh).
Posicionar IK_Foot_L/R colados ao foot_l/foot_r mas como bones IRMÃOS do root (não filhos do pelvis).
2.2. Convenção de orientação FBX (forward + up axis)
No Blender exporter:

Forward: -Y Forward (forward axis no FBX = X do Unreal, mas Blender chama de "Y Forward" devido a sua convenção; "-Y Forward" no exporter resulta em forward=X no UE)
Up: Z Up
Apply Unit: ON (resolve scale 100x do .blend pra cm do UE)
Apply Transform: ON (achata transforms do armature/mesh, evita rotação visível no UE)
2.3. Hierarquia de bones esperada
Nomenclatura obrigatória (case-sensitive):

Tudo lowercase: spine_01, head_01, hand_l, hand_r
Sufixos _l / _r (NÃO .L / .R do Blender — exportador converte automaticamente; verificar no FBX final).
Numeração com _01, _02 (zero à esquerda).
2.4. Sockets necessários (opcional mas recomendado)
Bones vazios usados como anchors para props/câmera:

Socket	Bone pai	Uso
SOCKET_Camera	head_01	onde a câmera FP/TP é attachada
SOCKET_HandBall_R	hand_r	onde a bocha "gruda" durante carga do throw
SOCKET_HandBall_L	hand_l	(alternativo para canhotos)
Como criar no Blender: bone-filho do pai, prefixo SOCKET_, sem weights, length pequeno (1cm). UE detecta automaticamente como socket no import.

3. ANIMAÇÕES NECESSÁRIAS (separadas em CAMADAS)
O UE5 importa animações como AnimSequence (AS_*). Cada FBX deve conter UMA animação com UM nome claro. Não exportar tudo junto.

3.1. Locomoção base (já deve existir)
Camada: corpo inteiro. Loop. Root motion = OFF (jogo gerencia movement via CharacterMovementComponent).

Arquivo FBX	Duração	Descrição
AS_Char_Idle.fbx	4-6s loop	Personagem parado, respirando
AS_Char_Walk_F.fbx	1s loop	Andando pra frente
AS_Char_Walk_B.fbx	1s loop	Andando pra trás
AS_Char_Walk_L.fbx	1s loop	Andando pra esquerda (strafe)
AS_Char_Walk_R.fbx	1s loop	Andando pra direita (strafe)
AS_Char_Jog_F.fbx	0.5s loop	Trote pra frente
AS_Char_Jump_Start.fbx	0.3s	Início do pulo
AS_Char_Jump_Loop.fbx	0.5s loop	No ar
AS_Char_Jump_Land.fbx	0.3s	Aterrissagem
3.2. Throw / Bocce (gameplay específico)
Camada: braço direito (upper body). NÃO loop.

Arquivo FBX	Duração	Descrição
AS_Throw_Idle.fbx	1s loop	Postura preparado pra jogar, bola na mão
AS_Throw_Charge.fbx	1.5s	Braço pra trás carregando força
AS_Throw_Release.fbx	0.4s	Lança a bola pra frente
AS_Throw_Followup.fbx	0.6s	Recovery, braço volta neutro
3.3. AimOffset Poses (CRÍTICO — é o que falta pra layered turn funcionar)
Camada: head + spine_01 + spine_02 + neck_01. POSES ESTÁTICAS de 1 frame cada.

O artista cria 9 poses numa única animação OU 9 FBX separados. Recomendo um único FBX AS_AimOffset_Char.fbx com 9 frames.

Layout: matriz 3×3 (Yaw vs Pitch). Personagem parado em T-pose-like, só a cabeça/spine rotacionada.

Frame	Yaw (lateral)	Pitch (vertical)	Descrição
1	-90° (esquerda total)	+45° (cima)	olha pra cima-esquerda
2	0° (centro)	+45° (cima)	olha pra cima
3	+90° (direita total)	+45° (cima)	olha pra cima-direita
4	-90°	0° (frente)	olha pra esquerda
5	0°	0°	POSE CENTRAL (= idle aim, neutro)
6	+90°	0°	olha pra direita
7	-90°	-45° (baixo)	olha pra baixo-esquerda
8	0°	-45°	olha pra baixo
9	+90°	-45°	olha pra baixo-direita
Critérios visuais:

Cabeça gira MAIS que o tronco (proporção ~60/40). Ex: yaw 90 → cabeça 55°, neck 20°, spine_02 15°.
Pitch só na cabeça (45° max). Spine quase não inclina.
Sem deformação no pescoço (artista vai ajustar manualmente as rotações de cada bone, é trabalho braçal mas resulta em algo limpo).
Nada de braços, pernas, dedos mexerem. Só spine/neck/head.
Esse FBX vai virar BS_AimOffset_Char (BlendSpace) no UE. O AnimBP samples 1 das 9 poses interpolando com base no yaw/pitch que o C++ fornece.

3.4. Faciais (opcional, futuro)
Camada: ossos da face (se rig tiver). Ignorar por enquanto.

4. EXPORTAÇÃO FBX — CHECKLIST POR ARQUIVO
4.1. FBX do SKELETON (uma vez só, ou quando rig mudar)
Arquivo: SK_Manuel_Set00.fbx (mesh + bind pose + skeleton, sem animação)

Conteúdo na cena Blender antes de exportar:

✅ Armature
✅ Mesh do corpo, com modifier Armature aplicado-mas-não-collapsed (modifier permanece)
✅ Sockets (SOCKET_* bones)
❌ Nenhuma action ativa na NLA
❌ Nenhuma luz, câmera, empty
✅ T-pose ou A-pose como rest pose
Blender → File → Export → FBX (.fbx):

4.2. FBX das ANIMAÇÕES (um por animação)
Arquivo: AS_Char_Walk_F.fbx, AS_Throw_Charge.fbx, etc.

Conteúdo na cena Blender:

✅ Armature (SEM mesh — economia + UE só precisa do skeleton + tracks)
Alternativa: armature + mesh; UE ignora mesh se já tem skeleton importado. Mas FBX fica maior.

✅ A Action ativa na NLA com a animação que quer exportar.
❌ Sockets podem ficar (não atrapalham).
Export settings (diferenças em relação ao skeleton):

Importante por arquivo:

AS_AimOffset_Char.fbx: 9 frames, baked. UE importa como AnimSequence; depois converte pra BlendSpace1D ou BlendSpace2D.
Locomoção: marcar como looping no UE depois (não é flag do FBX).
Throw: NÃO loop. Adicionar notify events depois no UE (release, follow-through).
4.3. Pasta de entrega
5. VALIDAÇÃO ANTES DE ENTREGAR (artista roda no Blender)
Antes de exportar, validar no Blender:

5.1. Visual — N panel → Item
Selecionar head_01 em Edit Mode:

✅ Roll = 0.000
✅ Head em coordenada acima do neck_01 (Z maior)
✅ Tail acima do head (cadeia segue pra cima)
5.2. Script de validação (rodar no Blender Python Console)
5.3. Smoke test pós-import no UE
Importar SK_Manuel_Set00.fbx no UE5.
Abrir o skeleton no Skeleton Editor.
Selecionar bone head_01 → painel direito mostra orientação.
Verificar visualmente: flecha azul (Z local) aponta pra BAIXO ou pra TRÁS (não pra lateral).
Rotacionar manualmente o bone no editor com gizmo de rotação:
Yaw (Z) → cabeça vira lateral ✅
Pitch (Y) → cabeça sobe/desce ✅
Roll (X) → cabeça tomba pro ombro ✅
Se algum eixo girar errado → roll do bone ainda tá zoado, voltar ao Blender.
6. PROTOCOLO DE ENTREGA / VERSIONAMENTO
Cada entrega:

Pasta delivery/YYYY-MM-DD/ com todos os FBX
CHANGELOG.md listando o que mudou nesta versão
Screenshot validation.png mostrando viewport do Blender com axes ativados em T-pose
Se rig mudou: notar explicitamente "rig changed — needs UE re-import + Re-target all anims"
Não fazer:

❌ Editar bones depois de feitas animações sem avisar (quebra anims)
❌ Exportar .blend direto (UE não lê)
❌ Adicionar bones novos sem documentar (pode quebrar AnimBP/IK)
❌ Mudar nome de bone existente (quebra tudo que referencia)
7. REFERÊNCIAS TÉCNICAS (links pro artista estudar)
UE5 Skeleton convention: docs.unrealengine.com/5.0/en-US/skeletal-mesh-asset-reference-in-unreal-engine/
Blender → UE FBX Workflow (Allright Rig pattern): procurar "Blender to Unreal Engine skeleton convention"
Mannequin reference skeleton (pra comparar nomenclatura/orientação): vem grátis no Third Person Template do UE; baixar UE, criar projeto Third Person, abrir SKM_Manny e inspecionar bones.
AimOffset tutorial: "Unreal Engine 5 AimOffset BlendSpace tutorial" (vários no YouTube, padrão é o mesmo desde UE4).
8. PRIORIDADE DE TRABALHO (ordem sugerida)
Sanear roll dos bones spine/neck/head (sem isso, todo resto continua bugado).
Reexportar SK_Manuel_Set00.fbx com as novas convenções.
Criar AS_AimOffset_Char.fbx com as 9 poses.
Reexportar locomoção existente com as mesmas configs FBX (pra garantir consistência de scale/axis).
Animações de throw (se ainda não existem).
9. O QUE O CODE-SIDE FAZ DEPOIS DE RECEBER
Pra contexto do artista entender pra que serve cada coisa:

Skeleton FBX → vira SKEL_Char_Master (asset compartilhado por todos os personagens; biblioteca de anim é feita 1 vez e reusada).
Locomoção FBX → AnimSequences usadas no BlendSpace de locomoção do AnimBP.
Throw FBX → AnimMontages disparados por gameplay (no BeginCharge, OnRelease).
AimOffset FBX → vira BS_AimOffset_Char (BlendSpace 2D, eixo X=yaw -90→+90, eixo Y=pitch -45→+45). AnimBP faz Layered Blend per Bone com filtro em spine_01 pra aplicar só na metade de cima do corpo. C++ fornece os valores yaw/pitch via Pawn vars.