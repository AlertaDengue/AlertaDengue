-- Table: "Dengue_global".regional_saude

-- Add column nome_macroreg
ALTER TABLE "Dengue_global".regional_saude ADD COLUMN nome_macroreg character varying(32);
-- Add values to column namemacroreg for regional MG
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'TRIANGULO DO SUL' WHERE nome_regional='Uberaba';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'TRIANGULO DO NORTE' WHERE nome_regional='Uberlândia';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'TRIANGULO DO NORTE' WHERE nome_regional='Ituiutaba';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUL' WHERE nome_regional='Varginha';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUL' WHERE nome_regional='Pouso Alegre';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUL' WHERE nome_regional='Passos';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUL' WHERE nome_regional='Alfenas';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUL' WHERE nome_regional='Teófilo Otoni';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUDESTE' WHERE nome_regional='Ubá';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUDESTE' WHERE nome_regional='Leopoldina';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'SUDESTE' WHERE nome_regional='Juiz de Fora';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'OESTE' WHERE nome_regional='Divinópolis';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORTE' WHERE nome_regional='Pirapora';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORTE' WHERE nome_regional='Montes Claros';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORTE' WHERE nome_regional='Januária';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NOROESTE' WHERE nome_regional='Patos de Minas';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NOROESTE' WHERE nome_regional='Unaí';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORDESTE' WHERE nome_regional='Patos de Minas';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORDESTE' WHERE nome_regional='Teófilo Otoni';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'NORDESTE' WHERE nome_regional='Pedra Azul';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'LESTE DO SUL' WHERE nome_regional='Ponte Nova';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'LESTE DO SUL' WHERE nome_regional='Manhumirim';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'LESTE' WHERE nome_regional='Governador Valadares';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'LESTE' WHERE nome_regional='Coronel Fabriciano';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'CENTRO SUL' WHERE nome_regional='São João Del Rei';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'CENTRO SUL' WHERE nome_regional='Barbacena';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'CENTRO' WHERE nome_regional='Sete Lagoas';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'CENTRO' WHERE nome_regional='Itabira';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'CENTRO' WHERE nome_regional='Belo Horizonte';
UPDATE "Dengue_global".regional_saude SET nome_macroreg = 'JEQUITINHONHA' WHERE nome_regional='Diamantina';
