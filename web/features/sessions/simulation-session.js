import {api} from '../../services/api.js';

// Owns one process-local ARP/Ethernet session, never the canonical project or DOM.
export function createSimulationSessionController({getContext, onChange}) {
  let id = null;
  let generation = 0;
  let busy = false;
  let inFlight = null;
  let state = null;
  let diagnostic = null;
  let highlightedLinks = [];
  const pendingStops = new Set();
  const stopping = new Map();
  const missingSession = problem => problem.code === 'INVALID_PROJECT'
    && problem.message === 'simulation: unknown or expired session; start a new session';
  const getState = () => structuredClone({id, generation, busy, inFlight, state, diagnostic,
    highlightedLinks, pendingStopCount: pendingStops.size});
  const sameProject = context => {
    const now = getContext();
    return now.workspaceRevision === context.workspaceRevision
      && now.editRevision === context.editRevision
      && now.projectSnapshot === context.projectSnapshot;
  };
  const clear = () => {
    id = null; busy = false; inFlight = null;
    state = null; diagnostic = null; highlightedLinks = [];
  };
  const requestStop = sessionId => {
    if (stopping.has(sessionId)) return stopping.get(sessionId);
    const request = api('/api/simulation/stop', {sessionId}).then(data => {
      if (data.status !== 'STOPPED') throw new Error('Servern bekräftade inte Stop.');
      pendingStops.delete(sessionId);
      return true;
    }).catch(problem => {
      if (missingSession(problem)) {
        pendingStops.delete(sessionId);
        return true;
      }
      pendingStops.add(sessionId);
      return false;
    }).finally(() => { stopping.delete(sessionId); });
    stopping.set(sessionId, request);
    return request;
  };
  const invalidate = (serverGone = false) => {
    generation += 1;
    const previous = id;
    clear();
    if (previous && !serverGone) void requestStop(previous);
    onChange();
  };
  const clearInputResult = () => {
    diagnostic = null; highlightedLinks = []; onChange();
  };
  const setInputError = message => {
    if (!id || busy) return;
    diagnostic = {error: message}; highlightedLinks = []; onChange();
  };
  const start = async () => {
    if (id || busy) return;
    for (const sessionId of pendingStops) void requestStop(sessionId);
    const context = getContext();
    const token = ++generation;
    busy = true; inFlight = 'start'; diagnostic = null; highlightedLinks = []; onChange();
    const current = () => token === generation && !id && sameProject(context);
    try {
      const data = await api('/api/simulation/start', {
        project: JSON.parse(context.projectSnapshot),
      });
      if (current()) { id = data.sessionId; state = data; }
      else if (data.sessionId) void requestStop(data.sessionId);
    } catch (problem) {
      if (current()) diagnostic = {error: problem.message};
    } finally {
      if (token === generation) { busy = false; inFlight = null; onChange(); }
    }
  };
  const run = async (operation, sourceNode, sourcePort, target, readInputs) => {
    if (!id || busy) return;
    const sessionId = id;
    const context = getContext();
    const signature = readInputs();
    const token = ++generation;
    busy = true; inFlight = 'run'; diagnostic = null; highlightedLinks = []; onChange();
    const current = () => token === generation && id === sessionId && sameProject(context);
    try {
      const data = await api('/api/simulation/run', {
        sessionId, project: JSON.parse(context.projectSnapshot),
        operation, sourceNode, sourcePort, target,
      });
      if (current()) {
        state = data; // Preserve actual ARP/MAC learning and operation count.
        if (readInputs() === signature) {
          diagnostic = {data, sourceNode, sourcePort, target};
          const transmissions = operation === 'arp'
            ? [...data.result.requestTransmissions, ...data.result.replyTransmissions]
            : data.result.transmissions;
          highlightedLinks = [...new Set(transmissions.map(t => t.linkId))];
        }
      }
    } catch (problem) {
      if (current()) {
        if (missingSession(problem)) {
          invalidate(true);
          diagnostic = {error: 'Sessionen har upphört på servern. Starta en ny session.'};
          onChange();
        } else if (readInputs() === signature) {
          diagnostic = {error: problem.message}; highlightedLinks = [];
        }
      }
    } finally {
      if (token === generation) {
        if (!sameProject(context)) invalidate();
        else { busy = false; inFlight = null; onChange(); }
      }
    }
  };
  const reset = async () => {
    if (!id || (busy && inFlight !== 'run')) return;
    const sessionId = id;
    const context = getContext();
    const token = ++generation;
    busy = true; inFlight = 'reset'; onChange();
    const current = () => token === generation && id === sessionId && sameProject(context);
    try {
      const data = await api('/api/simulation/reset', {
        sessionId, project: JSON.parse(context.projectSnapshot),
      });
      if (current()) { state = data; diagnostic = null; highlightedLinks = []; }
    } catch (problem) {
      if (current()) {
        if (missingSession(problem)) {
          invalidate(true);
          diagnostic = {error: 'Sessionen har upphört på servern. Starta en ny session.'};
          onChange();
        } else diagnostic = {error: problem.message};
      }
    } finally {
      if (token === generation) {
        if (!sameProject(context)) invalidate();
        else { busy = false; inFlight = null; onChange(); }
      }
    }
  };
  const stop = async () => {
    if (!id) return;
    const sessionId = id;
    const token = ++generation;
    busy = true; inFlight = 'stop'; onChange();
    try {
      const removed = await requestStop(sessionId);
      if (token === generation && id === sessionId) {
        if (removed) clear();
        else diagnostic = {error: 'Kunde inte bekräfta Stop på servern. Försök igen.'};
      }
    } finally {
      if (token === generation) { busy = false; inFlight = null; onChange(); }
    }
  };
  return {getState, invalidate, clearInputResult, setInputError, start, run, reset, stop};
}
