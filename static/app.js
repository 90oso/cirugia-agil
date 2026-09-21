'use strict';


/* =========================================================
   GLOBALS
   ========================================================= */

const $ = (id) => document.getElementById(id);

let config = null;
let working = false;
let currentResult = null;


const symbols = {
  pass: '✓',
  fail: '×',
  missing: '!',
  review: '?'
};


const resultStates = {
  PREAPROBADO: 'pass',
  PREAPROBADA: 'pass',

  DOCUMENTOS_FALTANTES: 'missing',
  DOCUMENTOS_PENDIENTES: 'missing',

  NO_PREAPROBADA: 'fail',
  NO_CUBIERTO: 'fail',

  REVISION_HUMANA: 'review'
};


/* =========================================================
   DOM HELPERS
   ========================================================= */

function el(tag, text, className) {
  const node = document.createElement(tag);

  if (
    text !== undefined &&
    text !== null
  ) {
    node.textContent = String(text);
  }

  if (className) {
    node.className = className;
  }

  return node;
}


function notice(message, kind = '') {
  const node = $('global-message');

  node.textContent = message;
  node.className = `notice ${kind}`;
  node.hidden = !message;
}


/* =========================================================
   API
   ========================================================= */

async function api(path, options = {}) {
  const response = await fetch(
    path,
    options
  );

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(
      'El servidor no devolvió una respuesta válida. ' +
      'Revisa la terminal del proyecto.'
    );
  }

  if (!response.ok) {
    const detail = Array.isArray(
      data.detail
    )
      ? data.detail
          .map(item => item.msg)
          .join(' · ')
      : data.detail;

    throw new Error(
      detail ||
      'No se pudo completar la operación.'
    );
  }

  return data;
}


/* =========================================================
   HEALTH / CONFIG
   ========================================================= */

async function loadSystemStatus() {
  const pill = $('connection-pill');
  const text = $('connection-text');

  try {
    config = await api(
      '/api/health'
    );

    const aiOnline = Boolean(
      config.gemini_connected ??
      config.ollama_connected
    );

    const notionOnline = Boolean(
      config.notion_configured
    );

    if (
      config.default_model
    ) {
      $('model').value =
        config.default_model;
    }

    $('ai-state').textContent =
      aiOnline
        ? config.default_model ||
          'Gemini conectado'
        : 'No disponible';

    $('notion-state').textContent =
      notionOnline
        ? 'Notion conectado'
        : 'Sin configurar';

    const ready =
      aiOnline &&
      notionOnline &&
      Boolean(config.default_model);

    if (ready) {
      pill.className =
        'connection-pill online';

      text.textContent =
        'Sistema listo';
    } else {
      pill.className =
        'connection-pill offline';

      text.textContent =
        'Revisar configuración';
    }

    $('analyze-button').disabled =
      !ready;

    if (
      config.error
    ) {
      notice(
        config.error,
        'error'
      );
    }

  } catch (error) {
    pill.className =
      'connection-pill offline';

    text.textContent =
      'Servidor no disponible';

    $('ai-state').textContent =
      'Sin conexión';

    $('notion-state').textContent =
      'No disponible';

    $('analyze-button').disabled =
      true;

    notice(
      error.message,
      'error'
    );
  }
}


/* =========================================================
   VIEW MANAGEMENT
   ========================================================= */

function showView(view) {
  const newView =
    $('new-view');

  const historyView =
    $('history-view');

  newView.hidden =
    view !== 'new';

  historyView.hidden =
    view !== 'history';

  for (
    const name
    of ['new', 'history']
  ) {
    const tab =
      $(`${name}-tab`);

    const active =
      name === view;

    tab.classList.toggle(
      'active',
      active
    );

    if (active) {
      tab.setAttribute(
        'aria-current',
        'page'
      );
    } else {
      tab.removeAttribute(
        'aria-current'
      );
    }
  }

  if (view === 'new') {
    $('page-title').innerHTML =
      'Evalúa una solicitud quirúrgica ' +
      '<span>en minutos.</span>';

    $('page-subtitle').textContent =
      'El informe clínico se contrasta con la póliza, ' +
      'coberturas y requisitos registrados en Notion. ' +
      'Gemini interpreta la información y Python verifica ' +
      'las reglas antes de emitir el resultado preliminar.';
  }

  if (view === 'history') {
    $('page-title').innerHTML =
      'Historial de <span>evaluaciones.</span>';

    $('page-subtitle').textContent =
      'Consulta las solicitudes procesadas, sus resultados ' +
      'y los documentos utilizados durante la evaluación.';

    loadHistory();
  }
}


/* =========================================================
   REPORT FILE
   ========================================================= */

const reportInput =
  $('report');

const reportDrop =
  $('report-drop');


function updateReportName() {
  const file =
    reportInput.files[0];

  const name =
    $('report-name');

  if (file) {
    name.textContent =
      file.name;

    reportDrop.classList.add(
      'has-file'
    );
  } else {
    name.textContent =
      'Seleccionar informe médico';

    reportDrop.classList.remove(
      'has-file'
    );
  }
}


reportInput.addEventListener(
  'change',
  updateReportName
);


reportDrop.addEventListener(
  'dragover',
  (event) => {
    event.preventDefault();

    if (!working) {
      reportDrop.classList.add(
        'dragging'
      );
    }
  }
);


reportDrop.addEventListener(
  'dragleave',
  () => {
    reportDrop.classList.remove(
      'dragging'
    );
  }
);


reportDrop.addEventListener(
  'drop',
  (event) => {
    event.preventDefault();

    reportDrop.classList.remove(
      'dragging'
    );

    if (working) {
      return;
    }

    if (
      !event.dataTransfer.files.length
    ) {
      return;
    }

    const transfer =
      new DataTransfer();

    transfer.items.add(
      event.dataTransfer.files[0]
    );

    reportInput.files =
      transfer.files;

    updateReportName();
  }
);


/* =========================================================
   ATTACHMENTS
   ========================================================= */

const attachmentsInput =
  $('attachments');


function renderAttachments() {
  const container =
    $('attachment-list');

  container.replaceChildren();

  const files =
    Array.from(
      attachmentsInput.files
    );

  container.hidden =
    files.length === 0;

  files.forEach(
    (file, index) => {
      const item =
        el(
          'div',
          null,
          'attachment-item'
        );

      const icon =
        el(
          'span',
          '▤',
          'attachment-icon'
        );

      const meta =
        el(
          'div',
          null,
          'attachment-meta'
        );

      meta.append(
        el(
          'strong',
          file.name
        ),
        el(
          'span',
          formatBytes(file.size)
        )
      );

      const badge =
        el(
          'span',
          `Anexo ${index + 1}`,
          'attachment-badge'
        );

      item.append(
        icon,
        meta,
        badge
      );

      container.append(
        item
      );
    }
  );
}


attachmentsInput.addEventListener(
  'change',
  renderAttachments
);


function formatBytes(bytes) {
  if (
    !Number.isFinite(bytes)
  ) {
    return '';
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (
    bytes < 1024 * 1024
  ) {
    return (
      `${(
        bytes / 1024
      ).toFixed(1)} KB`
    );
  }

  return (
    `${(
      bytes /
      1024 /
      1024
    ).toFixed(1)} MB`
  );
}


/* =========================================================
   ANALYSIS
   ========================================================= */

$('analysis-form').addEventListener(
  'submit',
  async (event) => {
    event.preventDefault();

    if (working) {
      return;
    }

    const policyNumber =
      $('policy-number')
        .value
        .trim();

    const surgeryDate =
      $('surgery-date')
        .value;

    const report =
      $('report')
        .files[0];

    const attachments =
      Array.from(
        $('attachments')
          .files
      );

    if (!policyNumber) {
      notice(
        'Introduce el número de póliza.',
        'error'
      );

      return;
    }

    if (!surgeryDate) {
      notice(
        'Selecciona la fecha prevista de cirugía.',
        'error'
      );

      return;
    }

    if (!report) {
      notice(
        'Selecciona el informe médico.',
        'error'
      );

      return;
    }

    if (
      attachments.length > 3
    ) {
      notice(
        'Añade como máximo tres anexos.',
        'error'
      );

      return;
    }

    const files = [
      report,
      ...attachments
    ];

    if (
      files.some(
        file =>
          file.size >
          5 * 1024 * 1024
      )
    ) {
      notice(
        'Cada archivo debe ocupar como máximo 5 MB.',
        'error'
      );

      return;
    }

    if (
      !$('model').value
    ) {
      notice(
        'El modelo de IA no está disponible.',
        'error'
      );

      return;
    }

    notice('');

    const form =
      new FormData(
        $('analysis-form')
      );

    if (
      !attachments.length
    ) {
      form.delete(
        'attachments'
      );
    }

    working = true;

    $('result').hidden =
      true;

    $('analysis-progress').hidden =
      false;

    $('analyze-button').disabled =
      true;

    for (
      const control
      of $('analysis-form').elements
    ) {
      control.disabled =
        true;
    }

    const started =
      Date.now();

    const timer =
      setInterval(
        () => {
          const seconds =
            Math.round(
              (
                Date.now() -
                started
              ) / 1000
            );

          $('elapsed').textContent =
            `${seconds} s · ` +
            'Consultando Notion, analizando documentos ' +
            'y verificando las reglas.';
        },
        1000
      );

    try {
      const result =
        await api(
          '/api/analyze',
          {
            method: 'POST',
            body: form
          }
        );

      renderResult(
        result
      );

      $('result').scrollIntoView(
        {
          behavior: 'smooth',
          block: 'start'
        }
      );

    } catch (error) {
      notice(
        error.message,
        'error'
      );

      $('global-message')
        .scrollIntoView(
          {
            behavior: 'smooth',
            block: 'center'
          }
        );

    } finally {
      working = false;

      clearInterval(
        timer
      );

      $('analysis-progress').hidden =
        true;

      for (
        const control
        of $('analysis-form').elements
      ) {
        control.disabled =
          false;
      }

      $('analyze-button').disabled =
        false;
    }
  }
);


/* =========================================================
   RESULT
   ========================================================= */

function renderResult(data) {
  currentResult =
    data;

  const out =
    $('result');

  out.replaceChildren();
  out.hidden = false;

  const state =
    resultStates[
      data.status
    ] || 'review';


  /* -------------------------------------------------------
     Hero result
     ------------------------------------------------------- */

  const hero =
    el(
      'div',
      null,
      `result-hero result-${state}`
    );


  const marker =
    el(
      'div',
      symbols[state],
      `result-status-icon ${state}`
    );


  const heading =
    el(
      'div',
      null,
      'result-heading'
    );


  const label =
    el(
      'span',
      statusLabel(data.status),
      `result-status-label ${state}`
    );


  const title =
    el(
      'h2',
      data.title ||
      statusLabel(data.status)
    );

  title.id =
    'result-title';


  const summary =
    el(
      'p',
      data.summary || ''
    );


  heading.append(
    label,
    title,
    summary
  );


  hero.append(
    marker,
    heading
  );


  out.append(
    hero
  );


  /* -------------------------------------------------------
     Main metadata
     ------------------------------------------------------- */

  const patientStrip =
    el(
      'div',
      null,
      'patient-strip'
    );


  patientStrip.append(
    metaItem(
      'Paciente',
      data.patient ||
      'Sin identificar'
    ),

    metaItem(
      'Póliza',
      data.policy_number ||
      'Sin identificar'
    ),

    metaItem(
      'Procedimiento',
      data.procedure ||
      'Sin identificar'
    )
  );


  out.append(
    patientStrip
  );


  /* -------------------------------------------------------
     Summary dashboard
     ------------------------------------------------------- */

  const dashboard =
    el(
      'div',
      null,
      'result-dashboard'
    );


  const verified =
    data.checks.filter(
      check =>
        check.status ===
        'pass'
    ).length;


  const unresolved =
    data.checks.filter(
      check =>
        check.status !==
        'pass'
    ).length;


  dashboard.append(
    statCard(
      'Comprobaciones',
      `${verified}/${data.checks.length}`,
      unresolved === 0
        ? 'Todas verificadas'
        : `${unresolved} requieren atención`
    )
  );


  if (
    data.waiting
  ) {
    dashboard.append(
      statCard(
        'Carencia',
        `${data.waiting.elapsed_days} días`,
        `${data.waiting.required_days} días requeridos`
      )
    );
  }


  dashboard.append(
    statCard(
      'Documentos pendientes',
      String(
        data.missing_documents
          ?.length || 0
      ),
      (
        data.missing_documents
          ?.length
      )
        ? 'Requiere documentación'
        : 'Expediente completo'
    )
  );


  out.append(
    dashboard
  );


  /* -------------------------------------------------------
     Waiting period progress
     ------------------------------------------------------- */

  if (
    data.waiting
  ) {
    const waiting =
      renderWaiting(
        data.waiting
      );

    out.append(
      waiting
    );
  }


  /* -------------------------------------------------------
     Checks
     ------------------------------------------------------- */

  const checksHeader =
    el(
      'div',
      null,
      'checks-header'
    );

  checksHeader.append(
    el(
      'div',
      'Verificación detallada',
      'checks-title'
    ),
    el(
      'span',
      `${data.checks.length} controles`,
      'checks-count'
    )
  );


  out.append(
    checksHeader
  );


  const checksGrid =
    el(
      'div',
      null,
      'checks-grid'
    );


  data.checks.forEach(
    check => {
      checksGrid.append(
        renderCheck(
          check
        )
      );
    }
  );


  out.append(
    checksGrid
  );


  /* -------------------------------------------------------
     Missing documents
     ------------------------------------------------------- */

  if (
    data.missing_documents
    ?.length
  ) {
    const missing =
      el(
        'section',
        null,
        'missing-panel'
      );


    const missingHeader =
      el(
        'div',
        null,
        'missing-header'
      );


    missingHeader.append(
      el(
        'span',
        '!',
        'missing-icon'
      )
    );


    const text =
      el('div');

    text.append(
      el(
        'strong',
        'Documentación pendiente'
      ),
      el(
        'p',
        'Adjunta los documentos indicados y vuelve a evaluar la solicitud.'
      )
    );


    missingHeader.append(
      text
    );


    const list =
      el(
        'div',
        null,
        'missing-tags'
      );


    data.missing_documents
      .forEach(
        documentName => {
          list.append(
            el(
              'span',
              documentName
            )
          );
        }
      );


    missing.append(
      missingHeader,
      list
    );


    out.append(
      missing
    );
  }


  /* -------------------------------------------------------
     Notion sync
     ------------------------------------------------------- */

  out.append(
    renderNotionStatus(
      data
    )
  );


  /* -------------------------------------------------------
     Actions
     ------------------------------------------------------- */

  const actions =
    el(
      'div',
      null,
      'result-actions'
    );


  const download =
    el(
      'a',
      'Descargar resultado',
      'secondary-button'
    );

  download.href =
    `/api/cases/${data.id}/export`;

  download.download =
    `solicitud_${data.id.slice(0, 8)}.json`;


  const print =
    el(
      'button',
      'Imprimir',
      'secondary-button'
    );

  print.type =
    'button';

  print.addEventListener(
    'click',
    () => window.print()
  );


  actions.append(
    download,
    print
  );


  if (
    data.notion?.url
  ) {
    const notionLink =
      el(
        'a',
        'Abrir registro en Notion ↗',
        'notion-button'
      );

    notionLink.href =
      data.notion.url;

    notionLink.target =
      '_blank';

    notionLink.rel =
      'noopener noreferrer';

    actions.append(
      notionLink
    );

  } else if (
    data.notion_sync_error
  ) {
    const retry =
      el(
        'button',
        'Reintentar Notion',
        'notion-button'
      );

    retry.type =
      'button';

    retry.addEventListener(
      'click',
      async () => {
        retry.disabled =
          true;

        retry.textContent =
          'Guardando…';

        try {
          const notion =
            await api(
              `/api/cases/${data.id}/notion`,
              {
                method: 'POST'
              }
            );

          data.notion =
            notion;

          data.notion_sync_error =
            null;

          notice(
            'Resultado guardado correctamente en Notion.',
            'success'
          );

          renderResult(
            data
          );

        } catch (error) {
          notice(
            error.message,
            'error'
          );

          retry.disabled =
            false;

          retry.textContent =
            'Reintentar Notion';
        }
      }
    );

    actions.append(
      retry
    );
  }


  out.append(
    actions
  );


  /* -------------------------------------------------------
     Source files
     ------------------------------------------------------- */

  if (
    data.documents
    ?.length
  ) {
    const sources =
      el(
        'div',
        null,
        'source-section'
      );


    sources.append(
      el(
        'span',
        'Documentos utilizados',
        'source-title'
      )
    );


    const files =
      el(
        'div',
        null,
        'source-files'
      );


    data.documents.forEach(
      doc => {
        const link =
          el(
            'a',
            doc.name
          );

        link.href =
          `/api/cases/${data.id}/documents/${doc.id}`;

        link.download =
          doc.name;

        files.append(
          link
        );
      }
    );


    sources.append(
      files
    );


    out.append(
      sources
    );
  }


  out.append(
    el(
      'p',
      data.disclaimer ||
      'Resultado preliminar.',
      'result-disclaimer'
    )
  );
}


function statusLabel(status) {
  const labels = {
    PREAPROBADO:
      'PREAPROBADO',

    PREAPROBADA:
      'PREAPROBADO',

    DOCUMENTOS_FALTANTES:
      'DOCUMENTOS FALTANTES',

    DOCUMENTOS_PENDIENTES:
      'DOCUMENTOS FALTANTES',

    NO_PREAPROBADA:
      'NO PREAPROBADA',

    NO_CUBIERTO:
      'NO CUBIERTO',

    REVISION_HUMANA:
      'REVISIÓN HUMANA'
  };

  return (
    labels[status] ||
    status ||
    'RESULTADO'
  );
}


function metaItem(label, value) {
  const item =
    el(
      'div',
      null,
      'patient-meta'
    );

  item.append(
    el(
      'span',
      label
    ),

    el(
      'strong',
      value
    )
  );

  return item;
}


function statCard(
  label,
  value,
  description
) {
  const card =
    el(
      'div',
      null,
      'stat-card'
    );

  card.append(
    el(
      'span',
      label,
      'stat-label'
    ),

    el(
      'strong',
      value,
      'stat-value'
    ),

    el(
      'small',
      description,
      'stat-description'
    )
  );

  return card;
}


function renderWaiting(waiting) {
  const box =
    el(
      'section',
      null,
      'waiting-card'
    );


  const header =
    el(
      'div',
      null,
      'waiting-header'
    );


  const text =
    el('div');

  text.append(
    el(
      'span',
      'PERÍODO DE CARENCIA',
      'mini-kicker'
    ),

    el(
      'strong',
      waiting.remaining_days === 0
        ? 'Carencia cumplida'
        : 'Carencia pendiente'
    )
  );


  const numbers =
    el(
      'div',
      null,
      'waiting-numbers'
    );

  numbers.append(
    el(
      'strong',
      `${waiting.elapsed_days} días`
    ),

    el(
      'span',
      `de ${waiting.required_days} requeridos`
    )
  );


  header.append(
    text,
    numbers
  );


  box.append(
    header
  );


  const track =
    el(
      'div',
      null,
      'waiting-track'
    );


  const progress =
    el(
      'span',
      null,
      'waiting-progress'
    );


  const ratio =
    waiting.required_days > 0
      ? Math.min(
          1,
          waiting.elapsed_days /
          waiting.required_days
        )
      : 1;


  progress.style.width =
    `${ratio * 100}%`;


  track.append(
    progress
  );


  box.append(
    track
  );


  const footer =
    el(
      'div',
      null,
      'waiting-footer'
    );


  footer.append(
    el(
      'span',
      `Inicio elegible: ${waiting.eligible_date || '—'}`
    ),

    el(
      'span',
      waiting.remaining_days
        ? `${waiting.remaining_days} días restantes`
        : 'Sin días pendientes'
    )
  );


  box.append(
    footer
  );


  return box;
}


function renderCheck(check) {
  const item =
    el(
      'article',
      null,
      `check-card check-${check.status}`
    );


  const header =
    el(
      'div',
      null,
      'check-card-header'
    );


  const icon =
    el(
      'span',
      symbols[
        check.status
      ] || '?',
      `check-symbol ${check.status}`
    );


  const heading =
    el('div');

  heading.append(
    el(
      'h3',
      check.name
    ),

    el(
      'span',
      checkStatusText(
        check.status
      ),
      'check-state'
    )
  );


  header.append(
    icon,
    heading
  );


  item.append(
    header,
    el(
      'p',
      check.detail,
      'check-detail'
    )
  );


  if (
    check.evidence
    ?.length
  ) {
    const details =
      document.createElement(
        'details'
      );


    const summary =
      document.createElement(
        'summary'
      );

    summary.textContent =
      `Ver evidencia (${check.evidence.length})`;


    details.append(
      summary
    );


    check.evidence.forEach(
      proof => {
        const evidence =
          el(
            'blockquote',
            proof.quote,
            'evidence'
          );

        evidence.append(
          el(
            'cite',
            `${proof.document} · página ${proof.page} · ` +
            (
              proof.verified
                ? 'evidencia verificada'
                : 'sin verificar'
            )
          )
        );

        details.append(
          evidence
        );
      }
    );


    item.append(
      details
    );
  }


  return item;
}


function checkStatusText(status) {
  const labels = {
    pass: 'Verificado',
    missing: 'Pendiente',
    fail: 'No cumple',
    review: 'Revisar'
  };

  return (
    labels[status] ||
    'Revisar'
  );
}


function renderNotionStatus(data) {
  const box =
    el(
      'div',
      null,
      'notion-result'
    );


  const icon =
    el(
      'span',
      data.notion
        ? '✓'
        : '!',
      data.notion
        ? 'notion-result-icon success'
        : 'notion-result-icon warning'
    );


  const content =
    el('div');


  if (
    data.notion
  ) {
    content.append(
      el(
        'strong',
        'Resultado registrado en Notion'
      ),

      el(
        'p',
        'La solicitud y su estado quedaron almacenados automáticamente.'
      )
    );
  } else {
    content.append(
      el(
        'strong',
        'No se pudo registrar en Notion'
      ),

      el(
        'p',
        data.notion_sync_error ||
        'Puedes volver a intentarlo desde esta evaluación.'
      )
    );
  }


  box.append(
    icon,
    content
  );


  return box;
}


/* =========================================================
   HISTORY
   ========================================================= */

async function loadHistory() {
  const list =
    $('history-list');

  list.replaceChildren(
    el(
      'div',
      'Cargando evaluaciones…',
      'history-loading'
    )
  );

  try {
    const rows =
      await api(
        '/api/cases'
      );

    list.replaceChildren();

    if (
      !rows.length
    ) {
      const empty =
        el(
          'div',
          null,
          'empty-state'
        );

      empty.append(
        el(
          'span',
          '◇',
          'empty-symbol'
        ),

        el(
          'strong',
          'Todavía no hay evaluaciones.'
        ),

        el(
          'p',
          'Las solicitudes procesadas aparecerán aquí.'
        )
      );

      list.append(
        empty
      );

      return;
    }

    rows.forEach(
      item => {
        const row =
          el(
            'button',
            null,
            'history-row'
          );

        row.type =
          'button';


        const left =
          el(
            'div',
            null,
            'history-primary'
          );


        left.append(
          el(
            'strong',
            item.patient ||
            'Paciente sin identificar'
          ),

          el(
            'p',
            item.procedure ||
            'Procedimiento sin identificar'
          )
        );


        const center =
          el(
            'div',
            null,
            'history-date'
          );


        center.append(
          el(
            'span',
            item.policy_number ||
            'Sin póliza'
          ),

          el(
            'small',
            formatDateTime(
              item.created_at
            )
          )
        );


        const status =
          el(
            'span',
            statusLabel(
              item.status
            ),
            (
              'history-status ' +
              `status-${resultStates[item.status] || 'review'}`
            )
          );


        row.append(
          left,
          center,
          status
        );


        row.addEventListener(
          'click',
          async () => {
            try {
              const result =
                await api(
                  `/api/cases/${item.id}`
                );

              showView(
                'new'
              );

              renderResult(
                result
              );

              $('result')
                .scrollIntoView(
                  {
                    behavior: 'smooth',
                    block: 'start'
                  }
                );

            } catch (error) {
              notice(
                error.message,
                'error'
              );
            }
          }
        );


        list.append(
          row
        );
      }
    );

  } catch (error) {
    list.replaceChildren(
      el(
        'div',
        error.message,
        'notice error'
      )
    );
  }
}


function formatDateTime(value) {
  if (!value) {
    return '';
  }

  try {
    return new Date(
      value
    ).toLocaleString(
      'es-PA',
      {
        dateStyle: 'medium',
        timeStyle: 'short'
      }
    );

  } catch {
    return value;
  }
}


/* =========================================================
   NAVIGATION
   ========================================================= */

$('new-tab').addEventListener(
  'click',
  () => showView('new')
);


$('history-tab').addEventListener(
  'click',
  () => showView('history')
);


$('refresh-history').addEventListener(
  'click',
  loadHistory
);


/* =========================================================
   INITIALIZATION
   ========================================================= */

loadSystemStatus();