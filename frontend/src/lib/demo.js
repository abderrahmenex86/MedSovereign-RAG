/**
 * Backend-free demo stream.
 *
 * This is deliberately explicit: it only runs with `?demo=1` or
 * VITE_DEMO_MODE=true, and the UI shows a Demo badge. It never masks a failing
 * backend.
 */

const SOURCES = {
    bronchitis: [
        {
            chunk_id: 'GUIDE-ACB-1#body-0',
            doc_id: 'GUIDE-ACB-1',
            source: 'guideline',
            title: 'Acute bronchitis: clinical practice guideline',
            published: '2023',
            section: 'Recommendations',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Clinical Guidance', publication_types: ['Practice Guideline'] },
            text: 'Acute bronchitis is usually viral. Antibiotics are not routinely indicated for uncomplicated cases; reserve them for suspected bacterial infection. Rest, fluids, and antipyretics are the mainstays of supportive care.',
            rerank_score: 8.7,
        },
        {
            chunk_id: 'REV-ACB-2#body-0',
            doc_id: 'REV-ACB-2',
            source: 'review',
            title: 'Symptom management in acute bronchitis',
            published: '2021',
            section: 'Abstract',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Respiratory Reviews', publication_types: ['Systematic Review'] },
            text: 'A persistent cough may last 10 to 20 days. Wheezing and chest tightness can be managed with inhaled bronchodilators when indicated. Humidified air may help loosen secretions.',
            rerank_score: 7.9,
        },
        {
            chunk_id: 'SR-ACB-3#body-0',
            doc_id: 'SR-ACB-3',
            source: 'review',
            title: 'Antibiotic prescribing for acute bronchitis',
            published: '2019',
            section: 'Results',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Evidence in Primary Care', publication_types: ['Meta-Analysis'] },
            text: 'Most randomized trials show little benefit from antibiotics in uncomplicated acute bronchitis, while adverse effects and resistance increase. Shared decision making is recommended.',
            rerank_score: 7.1,
        },
    ],
    diabetes: [
        {
            chunk_id: 'GUIDE-T2D-1#body-0',
            doc_id: 'GUIDE-T2D-1',
            source: 'guideline',
            title: 'Management of newly diagnosed type 2 diabetes',
            published: '2024',
            section: 'Recommendations',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Clinical Guidance', publication_types: ['Practice Guideline'] },
            text: 'Start with lifestyle change and metformin for most adults with newly diagnosed type 2 diabetes. Individualize the A1c target and add a GLP-1 receptor agonist or SGLT2 inhibitor when cardiovascular or kidney disease is present.',
            rerank_score: 9.0,
        },
        {
            chunk_id: 'REV-T2D-2#body-0',
            doc_id: 'REV-T2D-2',
            source: 'review',
            title: 'First-line pharmacotherapy for type 2 diabetes',
            published: '2022',
            section: 'Abstract',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Metabolic Evidence', publication_types: ['Systematic Review'] },
            text: 'Metformin remains the usual first-line agent. Choice of add-on therapy should account for cardiovascular risk, kidney function, weight goals, hypoglycemia risk, and cost.',
            rerank_score: 8.2,
        },
    ],
    backpain: [
        {
            chunk_id: 'GUIDE-LBP-1#body-0',
            doc_id: 'GUIDE-LBP-1',
            source: 'guideline',
            title: 'Acute low back pain: red flags and initial care',
            published: '2023',
            section: 'Assessment',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Clinical Guidance', publication_types: ['Practice Guideline'] },
            text: 'Screen for red flags: progressive neurological deficit, bowel or bladder dysfunction, saddle anesthesia, fever, unexplained weight loss, cancer history, recent significant trauma, and intravenous drug use. Most uncomplicated cases improve with activity and simple analgesia.',
            rerank_score: 8.8,
        },
        {
            chunk_id: 'REV-LBP-2#body-0',
            doc_id: 'REV-LBP-2',
            source: 'review',
            title: 'Imaging in acute low back pain',
            published: '2020',
            section: 'Conclusions',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Musculoskeletal Reviews', publication_types: ['Systematic Review'] },
            text: 'Routine imaging is not indicated without red flags or progressive symptoms. Early imaging can increase downstream intervention without improving outcomes.',
            rerank_score: 7.6,
        },
    ],
    acl: [
        {
            chunk_id: 'PMID:36731908#body-0',
            doc_id: 'PMID:36731908',
            source: 'pubmed',
            title: 'Aspetar clinical practice guideline on rehabilitation after anterior cruciate ligament reconstruction',
            published: '2023-May',
            section: 'Abstract',
            pmid: '36731908',
            url: 'https://pubmed.ncbi.nlm.nih.gov/36731908/',
            license: 'PubMed abstract; publisher terms apply',
            meta: { journal: 'British Journal of Sports Medicine' },
            text: 'Exercise interventions should be considered the mainstay of ACLR rehabilitation. Physical therapy modalities can be helpful as an adjunct in the early phase when pain, swelling, and limited range of motion are present. Return to running and return to training are key milestones.',
            rerank_score: 8.9,
        },
        {
            chunk_id: 'GUIDE-ACL-2#body-0',
            doc_id: 'GUIDE-ACL-2',
            source: 'guideline',
            title: 'Rehabilitation milestones after ACL reconstruction',
            published: '2022',
            section: 'Recommendations',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'Sports Rehabilitation Guidance' },
            text: 'Progression should be criteria-based rather than time-based, with attention to swelling, quadriceps strength, and movement quality before advancing loading and running.',
            rerank_score: 7.8,
        },
    ],
    default: [
        {
            chunk_id: 'DEMO-1#body-0',
            doc_id: 'DEMO-1',
            source: 'demo',
            title: 'Frontend demo evidence',
            published: '2026',
            section: '',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'MedSovereign UI demo' },
            text: 'This is a simulated source used to preview the interface. The production pipeline retrieves real passages, reranks them, drafts an answer, and checks it with a judge before showing the result.',
            rerank_score: 6.2,
        },
        {
            chunk_id: 'DEMO-2#body-0',
            doc_id: 'DEMO-2',
            source: 'demo',
            title: 'About this demo',
            published: '2026',
            section: '',
            pmid: '',
            url: '',
            license: 'Demo content',
            meta: { journal: 'MedSovereign UI demo' },
            text: 'Demo mode runs entirely in the browser. Ask one of the suggested clinical questions to see a representative answer with citations, sources, and a reasoning trace.',
            rerank_score: 5.8,
        },
    ],
};

const ANSWERS = {
    bronchitis: `For uncomplicated acute bronchitis:

- **Symptoms:** persistent cough (often 10–20 days), wheezing, low fever, chest tightness.
- **Supportive care:** rest, fluids, acetaminophen or ibuprofen for fever, and humidified air.
- **Wheezing:** an inhaled bronchodilator may help when wheeze is prominent.
- **Antibiotics:** not routinely indicated; reserve them for suspected bacterial infection.

Most cases are viral and improve without antibiotics. [GUIDE-ACB-1]`,
    diabetes: `For most adults with newly diagnosed type 2 diabetes:

- Start with **lifestyle change and metformin**.
- Individualize the A1c target.
- Add a **GLP-1 receptor agonist or SGLT2 inhibitor** when cardiovascular or kidney disease is present.
- Reassess tolerability, cost, weight goals, and hypoglycemia risk at each step.

[GUIDE-T2D-1]`,
    backpain: `Screen for red flags before treating acute low back pain:

- Progressive neurological deficit
- Bowel or bladder dysfunction
- Saddle anesthesia
- Fever, unexplained weight loss, cancer history
- Recent significant trauma or intravenous drug use

Without red flags, routine imaging is not indicated. Most cases improve with activity and simple analgesia. [GUIDE-LBP-1]`,
    acl: `Exercise interventions are the mainstay of rehabilitation after ACL reconstruction. Physical therapy modalities can be an early adjunct when pain, swelling, and range-of-motion limits are present. Progression should be criteria-based, and return to running is a key milestone. [PMID:36731908]`,
    default: `This is a **frontend demo**, not a generated clinical answer.

In the running application, this space would contain an answer grounded in the retrieved passages, with citations, a judge decision, and a verifiable source list. Try one of the suggested questions to preview the full layout.`,
};

export function isDemoMode() {
    if (import.meta.env?.VITE_DEMO_MODE === 'true') return true;
    if (typeof window === 'undefined') return false;

    const value = new URLSearchParams(window.location.search).get('demo');
    return value === '1' || value === 'true';
}

export const DEMO_HEALTH = {
    status: 'ok',
    demo: true,
    device: 'browser demo',
    corpus_chunks: 24,
    corpus_documents: 8,
    corpus_format: 'jsonl',
    generator: 'demo stream',
    generator_backend: 'demo',
    startup_seconds: 0,
};

function scenarioFor(query) {
    const text = query.toLowerCase();

    if (text.includes('refuse') || text.includes('unverified')) return 'refused';
    if (text.includes('bronchitis') || text.includes('cough')) return 'bronchitis';
    if (text.includes('diabetes') || text.includes('glucose')) return 'diabetes';
    if (text.includes('back') || text.includes('spine')) return 'backpain';
    if (text.includes('acl') || text.includes('cruciate')) return 'acl';
    return 'default';
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const TITLES = {
    bronchitis: 'Acute bronchitis treatment',
    diabetes: 'Managing type 2 diabetes',
    backpain: 'Low back pain red flags',
    acl: 'ACL rehabilitation',
    default: 'Clinical evidence demo',
    refused: 'Unverified clinical question',
};

async function* eventStream(payload, signal) {
    const scenario = scenarioFor(payload.query || '');
    const started = Date.now();
    const attempt = {
        attempt: 1,
        query_used: payload.query,
        critique: 'PASS',
        outcome: 'passed',
    };

    yield { event: 'title', data: TITLES[scenario] };

    yield {
        event: 'status',
        step: 'search',
        message: `Attempt 1: Searching the literature for “${payload.query}”`,
    };

    await wait(500);
    if (signal?.aborted) return;

    if (scenario === 'refused') {
        yield {
            event: 'correction',
            message: 'No passage passed the relevance threshold. Rewriting query...',
        };
        await wait(600);
        if (signal?.aborted) return;

        yield {
            event: 'done',
            trace: {
                original_query: payload.query,
                iterations: [{ attempt: 1, query_used: payload.query, outcome: 'rejected' }],
                final_answer: null,
                status: 'REFUSED',
                attempts: 3,
                duration_s: (Date.now() - started) / 1000,
            },
        };
        return;
    }

    const sources = SOURCES[scenario] || SOURCES.default;
    const answer = ANSWERS[scenario] || ANSWERS.default;

    yield { event: 'sources', data: sources };

    yield {
        event: 'status',
        step: 'rerank',
        message: 'Cross-Encoder reranking candidates...',
    };
    await wait(450);
    if (signal?.aborted) return;

    yield {
        event: 'status',
        step: 'drafting',
        message: 'Drafting clinical response...',
    };
    await wait(350);

    for (const token of answer.match(/\S+\s*/g) || []) {
        if (signal?.aborted) return;
        yield { event: 'token', data: token };
        await wait(18);
    }

    if (signal?.aborted) return;

    yield {
        event: 'status',
        step: 'critique',
        message: 'Auditor evaluating response for hallucinations...',
    };
    await wait(500);
    if (signal?.aborted) return;

    yield {
        event: 'status',
        step: 'success',
        message: 'Critique PASSED. Answer verified.',
    };
    await wait(250);
    if (signal?.aborted) return;

    attempt.generated_answer = answer;
    yield {
        event: 'done',
        trace: {
            original_query: payload.query,
            iterations: [attempt],
            final_answer: answer,
            status: 'SUCCESS',
            attempts: 1,
            duration_s: (Date.now() - started) / 1000,
        },
    };
}

export async function* demoStreamQuery(payload, { signal } = {}) {
    yield* eventStream(payload, signal);
}
