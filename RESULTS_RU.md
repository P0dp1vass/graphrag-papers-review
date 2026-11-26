# Сохранённый прогон: что показать на экране

Это выдержка из прежнего прогона, не новый запуск. Для показа достаточно этой страницы: здесь записаны ответы и итоговые метрики без сырого JSON и временных меток.

## Один вопрос, два ответа

**Вопрос:** “What does RAG-FGO optimize, and how does its memory pool help?”

**Первый найденный источник:** `2611.17788v1`, *RAG-FGO: Dynamic Optimization of Query-Rewriting Agents for Generative RAG*. В сохранённом контексте `matched_names` содержит `rag-fgo`. У первичной аннотации формулировка: RAG-FGO **introduces** a memory pool, который накапливает удачные стратегии и уменьшает влияние шумной обратной связи.

**Без графовых связей — начало ответа:**

> RAG-FGO optimizes generative retrieval strategies, specifically focusing on query rewriting. Its memory pool helps by accumulating high-quality strategies across iterations, which mitigates the impact of stochasticity and noisy feedback on optimization stability.

**С графовыми связями — полный ответ:**

> RAG-FGO optimizes query rewriting as a non-differentiable black-box optimization problem in a mixed discrete-continuous space. Its memory pool helps by introducing an elite-preserving memory pool that accumulates high-quality strategies across iterations, thereby mitigating the impact of stochasticity and noisy feedback on optimization stability.

Вариант с графом подробнее формулирует задачу оптимизации, но оба передают основную пользу пула. **Ни в одном нет URL.** При этом во входных графовых фактах есть `RAG-FGO -IMPROVES-> ELITE_PRESERVING_MEMORY_POOL`: аннотация не говорит, что метод **улучшает сам пул**. Это пример, почему аннотация важнее автоматически извлечённой связи.

## Итог по пяти вопросам

| Показатель | Без связей | Со связями |
|---|---:|---:|
| Успешные вызовы | 5/5 | 5/5 |
| Остановка по лимиту ответа | 0 | 0 |
| Ответы со ссылкой на найденную статью, среди вопросов с ожидаемым источником | 1/4 | 1/4 |
| Среднее время этапа генерации | 28,6 с | 47,4 с |

Ожидаемая статья в топ-3 у **4 из 4** вопросов с ожидаемой статьёй. В обоих режимах модель не стала выдумывать актуальную цену видеокарты. Содержательный разбор с помощью ИИ не обнаружил явного выигрыша графа; набор маленький, не отложенный, не независимый. Время относится к генерации у клиента в том прогоне; оно включает эффекты загрузки и кеша, а не измеряет полную задержку API. В прогоне использовали `num_predict=256`; в копии текущего кода — `1024`.
