use bi_cliente

if object_id ('tempdb..#base_efetividade')  is not null drop table #base_efetividade
select 
  e.cod_pesquisa
, e.data
, e.cod_pessoa
,p.NOM_PESSOA
, e.cod_rota
, e.cod_loja
,c.foto_checkin
,c.foto_justificativa
,e.cod_supervisor
, e.planejado
, e.realizado -
(
    case
        when e.justificativa = 1 then
            case
                when c.fl_justificativa_elegivel = 1
                     or upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA'
                then 0
                else 1
            end
        else 0
    end
) as aderencia

, isnull(
    case
        when e.realizado = 1 then
            case
                when e.justificativa = 0 then 1
                else 0
            end
    end,0
) realizado

, e.justificativa -
(
    case
        when e.justificativa = 1 then
            case
                when c.fl_justificativa_elegivel = 1
                     or upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA'
                then 0
                else 1
            end
        else 0
    end
) as justificado

--, e.justificativa as justificado

, case
    when e.realizado = 0 then 1
    else 0
end
+
(
    case
        when e.justificativa = 1 then
            case
                when c.fl_justificativa_elegivel = 1
                     or upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA'
                then 0
                else 1
            end
        else 0
    end
) as pendente

--, case when e.realizado = 0 then 1 else 0 end pendente

, case
    when upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA' then 1
    else isnull(c.fl_justificativa_elegivel,0)
end as fl_justificativa_elegivel

, case
    when e.realizado = 1 then
        case
            when c.ausencia = 1 then
                case
                    when c.fl_justificativa_elegivel = 1
                         or upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA'
                    then 0
                    else 1
                end
            else 0
        end
    else 1
end as fl_justificativa_nao_elegivel

, UPPER(
    replace(
        replace(
            case
                when e.cod_pesquisa = 0 then 'JUSTIFICATIVA PENDENTE'
                else isnull(c.tipo_justificativa,'JUSTIFICATIVA PENDENTE')
            end,
        'SEM JUSTIFICATIVA','REALIZADO'),
    'FALTA REALIZADO','FALTA SEM JUSTIFICATIVA')
) tipo_justificativa

, upper(c.obs_ausencia) obs_justificativa

, case
    when upper(isnull(c.tipo_justificativa,'')) = 'LOJA DUPLICADA' then 'ELEGÍVEL'
    when e.realizado = 1 then
        case
            when c.ausencia = 1 then
                case
                    when c.fl_justificativa_elegivel = 1 then 'ELEGÍVEL'
                    else 'NÃO ELEGÍVEL'
                end
            else 'ELEGÍVEL'
        end
    else 'NÃO ELEGÍVEL'
end as perfil_justificativa

, c.status_coleta
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.distancia else null end else null end distancia
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.hora_checkin else null end else null end hora_checkin
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.hora_checkout else null end else null end hora_checkout
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.hora_transmissao else null end else null end hora_transmissao
, case when  e.realizado = 1 then case when  e.justificativa = 0 then   case when ch.hora_checkin_min = c.hora_checkin  then 1 else 0 end else null end else null end  fl_checkin
, case when  e.realizado = 1 then case when  e.justificativa = 0 then   case when ch.hora_checkout_max = c.hora_checkout  then 1 else 0 end else null end else null end  fl_checkout
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.permanencia_em_loja else null end else null end permanencia_em_loja 
, case when  e.realizado = 1 then case when  e.justificativa = 0 then   case when ch.hora_checkout_max = c.hora_checkout  then ch.permanencia_em_loja_dia_h else null end else null end else null end  permanencia_em_loja_dia_h
, case when  e.realizado = 1 then case when  e.justificativa = 0 then   case when ch.hora_checkout_max = c.hora_checkout  then ch.permanencia_em_loja_dia_m else null end else null end else null end  permanencia_em_loja_dia_m
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.longitude_loja else null end else null end longitude_loja
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.latitude_checkin else null end else null end latitude_checkin
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.longitude_checkin else null end else null end longitude_checkin
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.latitude_checkout else null end else null end latitude_checkout
, case when  e.realizado = 1 then case when  e.justificativa = 0 then  c.longitude_checkout else null end else null end longitude_checkout
, e.bi_id_loja	
,DATEPART(WEEK,E.DATA) SEMANA
, e.bi_id_coleta	
, e.bi_id_tempo	
, e.bi_id_pessoa	
, 1 qtd
, p.cod_perfil 
,CASE
WHEN E.REALIZADO >=1 and e.justificativa <>1 THEN 1 
ELSE 0
END porcentagem 
into #base_efetividade

from 
bi_f_efetividade e  
left join  bi_d_coleta c on c.bi_id_coleta = e.bi_id_coleta
left join bi_d_pessoa p on  p.cod_pessoa = e.cod_pessoa 

left join (	select 
	  t.bi_id_tempo
	, p.bi_id_pessoa
	, c.cod_pessoa
	, c.data
	, min(c.hora_checkin) hora_checkin_min 
	, max(c.hora_checkout) hora_checkout_max 
	, sum (cast(left (replace (c.permanencia_em_loja,'*','0'),2) as int)) * 60 +  sum (cast(right (replace (c.permanencia_em_loja,'*','0'),2) as int)) permanencia_em_loja_dia_m
	, right ('00'+ cast ( sum (cast(left (replace (c.permanencia_em_loja,'*','0'),2) as int))+(sum (cast(right (replace (c.permanencia_em_loja,'*','0'),2) as int))-sum (cast(right (replace (c.permanencia_em_loja,'*','0'),2) as int))%60 )/60as varchar),2)
	+':' + right ('00'+ cast ( sum (cast(right (replace (c.permanencia_em_loja,'*','0'),2) as int))%60as varchar),2) permanencia_em_loja_dia_h
	from bi_d_coleta c
	inner join bi_d_tempo t on t.DATA = c.DATA
	inner join bi_d_pessoa p on p.cod_pessoa = c.cod_pessoa
	where c.realizado_checkin = 1 and c.realizado_checkout = 1   and c.ausencia = 0
	group by
	  t.bi_id_tempo
	, p.bi_id_pessoa
	, c.cod_pessoa
	, c.data)ch on  ch.bi_id_pessoa = e.bi_id_pessoa and ch.bi_id_tempo = e.bi_id_tempo 
WHERE  e.data >= '2025-03-31'
and e.cod_pessoa not in (1, 2) and p.COD_PERFIL in (2,3) and e.cod_loja not in (1)
ORDER BY 2
-- roteiro errado 12/09
DELETE FROM #base_efetividade 
WHERE cod_loja IN (546,300,97,458,94,243,677,486,1194) 
AND data = '2025-09-12';

-- roteiro errado consultor
DELETE FROM #base_efetividade 
WHERE cod_loja IN (1703,1693) 
AND data = '2025-09-24';

-- roteiro errado consultor
DELETE FROM #base_efetividade 
WHERE cod_loja IN (1310,1484,1497,1498,1708) 
AND data = '2025-09-25';


-- consultor - visitas não planejadas
UPDATE #base_efetividade 
SET planejado = 0 
WHERE cod_pessoa = 19 
AND data < '2025-10-01';


-- após 01/10, remove apenas registros NÃO realizados daquele período específico
DELETE FROM #base_efetividade
WHERE cod_pessoa = 19 
AND realizado = 0 
AND data >= '2025-10-01'
AND data <  '2025-10-02';


-- caso isolado (mantido)
DELETE FROM #base_efetividade
WHERE cod_pessoa = 36 
AND data = '2025-11-20' 
AND realizado = 0;


-- intervalo fechado corretamente (ok)
DELETE FROM #base_efetividade
WHERE cod_pessoa = 50
AND realizado = 0
AND data >= '2026-01-23'
AND data <  '2026-01-24';


-- CORRIGIDO: evitar apagar "o futuro inteiro"
DELETE FROM #base_efetividade
WHERE cod_pessoa = 50
AND realizado = 0
AND data >= '2026-03-03'
AND data <  '2026-03-04';


-- ajustar com limite
DELETE FROM #base_efetividade
WHERE cod_pessoa = 22
AND cod_loja = 695
AND data >= '2026-03-12'
AND data <  '2026-03-13';


DELETE FROM #base_efetividade
WHERE cod_pessoa = 10
AND realizado = 0
AND data >= '2026-03-16'
AND data <  '2026-03-17';


-- REMOVIDA DUPLICIDADE (fica só um)
DELETE FROM #base_efetividade
WHERE cod_pessoa = 24
AND realizado = 0
AND data >= '2026-04-24';


DELETE FROM #base_efetividade
WHERE cod_pessoa = 11
AND realizado = 0
AND data >= '2026-04-16'
AND data <  '2026-04-17';

DELETE FROM #base_efetividade
WHERE cod_pessoa = 51
AND realizado = 0
AND data >= '2026-05-11'
AND data <  '2026-05-12';

-- CORRIGIDO: evitar apagar "o futuro inteiro"
DELETE FROM #base_efetividade
WHERE cod_pessoa = 50
AND realizado = 0
AND data >= '2026-06-23'
AND data <  '2026-06-24';

-- CORRIGIDO: evitar apagar "o futuro inteiro"
DELETE FROM #base_efetividade
WHERE cod_pessoa = 50
AND realizado = 0
AND data >= '2026-07-02'
AND data <  '2026-07-03';

DELETE FROM #base_efetividade
WHERE cod_pessoa = 22
AND realizado = 0
AND data >= '2026-07-08'
AND data <  '2026-07-09';

DELETE FROM #base_efetividade
WHERE cod_pessoa = 16
AND realizado = 0
AND data >= '2026-08-14'
AND data <  '2026-08-15';


-- consultor: 19/10/2026 ainda em treinamento, subiram lojas erradas - desconsidera o dia inteiro
DELETE FROM #base_efetividade
WHERE NOM_PESSOA LIKE 'consultor FIGUEIREDO%'
AND data >= '2026-10-19'
AND data <  '2026-10-20';

-- consultor: 26/10/2026 feriado na regiao - remove so o que nao foi realizado
DELETE FROM #base_efetividade
WHERE NOM_PESSOA LIKE 'consultor FIGUEIREDO%'
AND realizado = 0
AND data >= '2026-10-26'
AND data <  '2026-10-27';


-- ajuste pontual mantido
UPDATE #base_efetividade 
SET planejado = 0 
WHERE cod_pessoa = 36 
AND data = '2025-12-08' 
AND justificado = 1;

--select final
select *
from #base_efetividade



