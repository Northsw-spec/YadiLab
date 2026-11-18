import {api} from '../../services/api.js';

// Owns one ICMP Investigation; the canonical project and DOM remain in app.js.
export function createIcmpInvestigationController({getContext, onChange}) {
  let id = null;
  let state = null;
  let generation = 0;
  let busy = false;
  let log = [];
  let verdict = null;
  let recovery = null;
  let error = null;
  const pendingStops = new Set();
  const stopping = new Map();
  const missingSession = problem => problem.code === 'INVALID_PROJECT'
    && problem.message === 'icmp investigation: unknown or expired session';
  const view = () => structuredClone({id, state, generation, busy, log,
    verdict, recovery, error, pendingStopCount: pendingStops.size});
  const changed = () => onChange();
  const sameProject = context => {
    const now = getContext();
    return now.workspaceRevision === context.workspaceRevision
      && now.editRevision === context.editRevision
      && now.projectSnapshot === context.projectSnapshot;
  };
  const requestStop = sessionId => {
    if (stopping.has(sessionId)) return stopping.get(sessionId);
    const request = api('/api/icmp/investigation/stop', {sessionId})
      .then(data => {
        if (data.status !== 'STOPPED') throw new Error('Servern bekräftade inte Stop.');
        pendingStops.delete(sessionId);
        return true;
      }).catch(problem => {
        if (missingSession(problem)) {
          pendingStops.delete(sessionId);
          return true; // This ID has no server resource to release.
        }
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
    verdict = null; recovery = null; error = null;
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
    const signature = readInputs();
    const token = ++generation;
    busy = true; error = null; log = []; verdict = null; recovery = null;
    changed();
    const current = () => token === generation && !id
      && sameProject(context) && readInputs() === signature;
    try {
      const data = await api('/api/icmp/investigation/start', {
        project: JSON.parse(context.projectSnapshot), ...inputs,
      });
      if (current()) { id = data.sessionId; state = data; }
      else if (data.sessionId) void requestStop(data.sessionId);
    } catch (problem) {
      if (current()) error = problem.message;
    } finally {
      if (token === generation) { busy = false; changed(); }
    }
  };
  const operate = async (path, fields, readInputs, apply, reject) => {
    if (!id || busy) return;
    const sessionId = id;
    const context = getContext();
    const signature = readInputs?.();
    const token = ++generation;
    busy = true; error = null;
    changed();
    const current = () => token === generation && id === sessionId
      && sameProject(context);
    try {
      const data = await api('/api/icmp/investigation/' + path, {
        sessionId, project: JSON.parse(context.projectSnapshot), ...fields,
      });
      if (current()) {
        if (!readInputs || readInputs() === signature) apply(data);
        else {
          state = data; // The server processed the old input, but it is not current evidence.
          error = path === 'diagnose'
            ? 'En tidigare hypotes behandlades. Avsluta och starta om för tydlig diagnos.'
            : 'En tidigare mätning behandlades men dess målval ändrades. Mät på nytt.';
        }
      }
    } catch (problem) {
      if (current()) {
        if (missingSession(problem)) {
          invalidate(true);
          setInputError('Sessionen har upphört på servern. Starta en ny ICMP-övning.');
        } else if (!readInputs || readInputs() === signature) reject(problem);
      }
    } finally {
      if (token === generation) { busy = false; changed(); }
    }
  };
  const probe = (kind, target, readInputs) => {
    if (!id || busy || state?.repaired) return;
    return operate('probe', {probe: kind, target}, readInputs, data => {
      state = data;
      log.push({probe: kind, observation: data.observation});
    }, problem => { log.push({error: problem.message}); });
  };
  const diagnose = (diagnosis, readInputs) => {
    if (!id || busy || !state?.canDiagnose || state.diagnosed) return;
    return operate('diagnose', {diagnosis}, readInputs, data => {
      state = data; verdict = data;
    }, problem => { verdict = {error: problem.message}; });
  };
  const repair = () => {
    if (!id || busy || !state?.diagnosed || state.repaired || !verdict?.correct) return;
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
        else error = 'Kunde inte bekräfta Stop på servern. Försök igen.';
      }
    } finally {
      if (token === generation) { busy = false; changed(); }
    }
  };
  return {getState: view, setInputError, start, probe, diagnose, repair, stop, invalidate};
}
