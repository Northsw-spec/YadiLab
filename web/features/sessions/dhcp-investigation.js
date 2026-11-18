import {api} from '../../services/api.js';

// Owns only one DHCP Investigation. Project and UI inputs remain in the app.
export function createDhcpInvestigationController({getContext, onChange}) {
  let id = null;
  let state = null;
  let generation = 0;
  let busy = false;
  let log = [];
  let verdict = null;
  let recovery = null;
  let error = null;
  let clockEvent = null;
  const pendingStops = new Set();
  const stopping = new Map();
  const missingSession = problem => problem.code === 'INVALID_PROJECT'
    && problem.message === 'investigation: unknown or expired session';

  const view = () => structuredClone({id, state, generation, busy, log, verdict,
    recovery, error, clockEvent, pendingStopCount: pendingStops.size});
  const changed = () => onChange();
  const sameContext = (context, readInputs, inputs) => {
    const now = getContext();
    return now.workspaceRevision === context.workspaceRevision
      && now.editRevision === context.editRevision
      && now.projectSnapshot === context.projectSnapshot
      && (!readInputs || readInputs() === inputs);
  };
  const requestStop = sessionId => {
    if (stopping.has(sessionId)) return stopping.get(sessionId);
    const request = api('/api/dhcp/investigation/stop', {sessionId})
      .then(() => { pendingStops.delete(sessionId); return true; })
      .catch(() => {
        // Keep the exact orphan ID for a later explicit retry. No cleanup claim.
        pendingStops.add(sessionId);
        return false;
      }).finally(() => { stopping.delete(sessionId); });
    stopping.set(sessionId, request);
    return request;
  };
  const retryPendingStops = () => {
    for (const sessionId of pendingStops) void requestStop(sessionId);
  };
  const clear = () => {
    id = null; state = null; busy = false; log = [];
    verdict = null; recovery = null; error = null; clockEvent = null;
  };
  const invalidate = (serverGone = false) => {
    generation += 1;
    const previous = id;
    clear();
    if (previous && !serverGone) void requestStop(previous);
    changed();
  };
  const setInputError = message => {
    if (id || busy) return;
    error = message;
    changed();
  };

  const start = async (inputs, readInputs) => {
    if (id || busy) return;
    retryPendingStops();
    const context = getContext();
    const inputSignature = readInputs();
    const token = ++generation;
    busy = true; error = null; log = [];
    verdict = null; recovery = null; clockEvent = null;
    changed();
    const current = () => token === generation && !id
      && sameContext(context, readInputs, inputSignature);
    try {
      const data = await api('/api/dhcp/investigation/start', {
        project: JSON.parse(context.projectSnapshot), ...inputs,
      });
      if (current()) { id = data.sessionId; state = data; }
      else if (data.sessionId) void requestStop(data.sessionId);
    } catch (problem) {
      if (current()) error = problem.message;
    } finally {
      if (token === generation) {
        if (!sameContext(context, readInputs, inputSignature)) invalidate();
        else { busy = false; changed(); }
      }
    }
  };

  const operate = async (path, fields, readInputs, apply, reject) => {
    if (!id || busy) return;
    const sessionId = id;
    const context = getContext();
    const inputSignature = readInputs?.();
    const token = ++generation;
    busy = true;
    changed();
    const current = () => token === generation && id === sessionId
      && sameContext(context, readInputs, inputSignature);
    try {
      const data = await api('/api/dhcp/investigation/' + path, {
        sessionId, project: JSON.parse(context.projectSnapshot), ...fields,
      });
      if (current()) apply(data);
    } catch (problem) {
      if (current()) {
        if (missingSession(problem)) {
          invalidate(true);
          setInputError('Sessionen har upphört på servern. Starta en ny övning.');
        } else reject(problem);
      }
    } finally {
      if (token === generation) {
        if (!sameContext(context, readInputs, inputSignature)) invalidate();
        else { busy = false; changed(); }
      }
    }
  };

  const advance = () => {
    if (!id || busy || !state?.canAdvance) return;
    const seconds = state.nextClockTargetSeconds - state.clockSeconds;
    if (!Number.isInteger(seconds) || seconds <= 0) return;
    clockEvent = null;
    return operate('advance', {seconds}, null, data => {
      state = data; clockEvent = data;
      log.push({probe: 'advance', observation: data});
    }, problem => { clockEvent = {error: problem.message}; });
  };
  const probe = (kind, target, readInputs) => {
    if (!id || busy || state?.repaired) return;
    error = null;
    return operate('probe', {probe: kind, target}, readInputs, data => {
      state = data;
      log.push({probe: kind, observation: data.observation});
    }, problem => { log.push({error: problem.message}); });
  };
  const diagnose = (diagnosis, readInputs) => {
    if (!id || busy || state?.diagnosed) return;
    return operate('diagnose', {diagnosis}, readInputs, data => {
      state = data; verdict = data;
    }, problem => { verdict = {error: problem.message}; });
  };
  const repair = () => {
    if (!id || busy || !state?.diagnosed || state.repaired) return;
    return operate('repair', {}, null, data => {
      state = data; recovery = data;
    }, problem => { recovery = {error: problem.message}; });
  };
  const stop = async () => {
    if (!id) return;
    const sessionId = id;
    const token = ++generation;
    busy = true;
    changed();
    try {
      const removed = await requestStop(sessionId);
      if (token === generation && id === sessionId) {
        if (removed) clear();
        else error = 'Kunde inte avsluta sessionen på servern. Försök igen.';
      }
    } finally {
      if (token === generation) { busy = false; changed(); }
    }
  };

  return {getState: view, setInputError, start, advance, probe, diagnose, repair, stop, invalidate};
}
