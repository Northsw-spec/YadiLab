import {api} from '../../services/api.js';

// Owns one process-local DORA session; project data and input choices stay in app.js.
export function createDoraSessionController({getContext, onChange}) {
  let id = null;
  let generation = 0;
  let busy = false;
  let state = null;
  let trace = null;
  let clockEvent = null;
  let renewalTrace = null;
  let faultEvent = null;
  let portFaultEvent = null;
  let vlanFaultEvent = null;
  const pendingStops = new Set();
  const stopping = new Map();
  const missingSession = problem => problem.code === 'INVALID_PROJECT'
    && problem.message === 'dhcp session: unknown or expired session; start a new session';
  const getState = () => structuredClone({id, generation, busy, state, trace,
    clockEvent, renewalTrace, faultEvent, portFaultEvent, vlanFaultEvent,
    pendingStopCount: pendingStops.size});
  const sameProject = context => {
    const now = getContext();
    return now.workspaceRevision === context.workspaceRevision
      && now.editRevision === context.editRevision
      && now.projectSnapshot === context.projectSnapshot;
  };
  const clear = () => {
    id = null; busy = false; state = null; trace = null; clockEvent = null;
    renewalTrace = null; faultEvent = null; portFaultEvent = null; vlanFaultEvent = null;
  };
  const requestStop = sessionId => {
    if (stopping.has(sessionId)) return stopping.get(sessionId);
    const request = api('/api/dhcp/session/stop', {sessionId}).then(data => {
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
  const setEventError = (event, message) => {
    if (busy) return;
    if (event === 'trace') trace = {error: message};
    else if (event === 'clockEvent') clockEvent = {error: message};
    else if (event === 'renewalTrace') renewalTrace = {error: message};
    else if (event === 'faultEvent') faultEvent = {error: message};
    onChange();
  };
  const clearInputResults = kind => {
    if (kind === 'client') { trace = null; renewalTrace = null; }
    if (kind === 'link') faultEvent = null;
    if (kind === 'port') { portFaultEvent = null; vlanFaultEvent = null; }
    onChange();
  };
  const start = async (fields, readInputs) => {
    if (id || busy) return;
    for (const sessionId of pendingStops) void requestStop(sessionId);
    const context = getContext();
    const signature = readInputs();
    const token = ++generation;
    clear(); busy = true; onChange();
    const current = () => token === generation && !id && sameProject(context)
      && readInputs() === signature;
    try {
      const data = await api('/api/dhcp/session/start', {
        project: JSON.parse(context.projectSnapshot), ...fields,
      });
      if (current()) { id = data.sessionId; state = data; }
      else if (data.sessionId) void requestStop(data.sessionId);
    } catch (problem) {
      if (current()) trace = {error: problem.message};
    } finally {
      if (token === generation) { busy = false; onChange(); }
    }
  };
  const operate = async (path, fields, readInputs, event, apply) => {
    if (!id || busy) return;
    const sessionId = id;
    const context = getContext();
    const signature = readInputs?.();
    const token = ++generation;
    busy = true;
    if (event === 'trace') trace = null;
    else if (event === 'renewalTrace') renewalTrace = null;
    else if (event === 'faultEvent') faultEvent = null;
    else if (event === 'portFaultEvent') portFaultEvent = null;
    else if (event === 'vlanFaultEvent') vlanFaultEvent = null;
    else if (event === 'clockEvent') clockEvent = null;
    onChange();
    const current = () => token === generation && id === sessionId && sameProject(context);
    try {
      const data = await api('/api/dhcp/session/' + path, {
        sessionId, project: JSON.parse(context.projectSnapshot), ...fields,
      });
      if (current()) {
        state = data; // A processed operation changes the real server session.
        if (!readInputs || readInputs() === signature) apply(data);
      }
    } catch (problem) {
      if (current()) {
        if (missingSession(problem)) {
          invalidate(true);
          trace = {error: 'Sessionen har upphört på servern. Starta en ny DHCP-session.'};
          onChange();
        } else if (!readInputs || readInputs() === signature) {
          if (event === 'trace') trace = {error: problem.message};
          else if (event === 'renewalTrace') renewalTrace = {error: problem.message};
          else if (event === 'clockEvent') clockEvent = {error: problem.message};
          else if (event === 'faultEvent') faultEvent = {error: problem.message};
          else if (event === 'portFaultEvent') portFaultEvent = {error: problem.message};
          else if (event === 'vlanFaultEvent') vlanFaultEvent = {error: problem.message};
        }
      }
    } finally {
      if (token === generation) {
        if (!sameProject(context)) invalidate();
        else { busy = false; onChange(); }
      }
    }
  };
  const run = (fields, readInputs) => operate('run', fields, readInputs, 'trace', data => {
    trace = data.result; clockEvent = null; renewalTrace = null;
  });
  const renew = (fields, readInputs) => operate('renew', fields, readInputs, 'renewalTrace', data => {
    renewalTrace = data.result; trace = null; clockEvent = null;
  });
  const advance = (seconds, readInputs) => operate('advance', {seconds}, readInputs, 'clockEvent', data => {
    trace = null; clockEvent = data; renewalTrace = null;
  });
  const reset = () => operate('reset', {}, null, 'trace', () => {
    trace = null; clockEvent = null; renewalTrace = null;
    faultEvent = null; portFaultEvent = null; vlanFaultEvent = null;
  });
  const linkFault = (linkId, disabled, readInputs) =>
    operate('link-fault', {linkId, disabled}, readInputs, 'faultEvent', () => {
      faultEvent = {linkId, disabled}; trace = null; renewalTrace = null; clockEvent = null;
    });
  const switchFault = (kind, nodeId, portId, parameter, readInputs) =>
    operate(kind === 'port' ? 'port-fault' : 'vlan-fault',
      {nodeId, portId, ...parameter}, readInputs,
      kind === 'port' ? 'portFaultEvent' : 'vlanFaultEvent', () => {
        if (kind === 'port') portFaultEvent = {nodeId, portId, ...parameter};
        else vlanFaultEvent = {nodeId, portId, ...parameter};
        trace = null; renewalTrace = null; clockEvent = null; faultEvent = null;
      });
  const stop = async () => {
    if (!id) return;
    const sessionId = id;
    const token = ++generation;
    busy = true; onChange();
    try {
      const removed = await requestStop(sessionId);
      if (token === generation && id === sessionId) {
        if (removed) clear();
        else trace = {error: 'Kunde inte bekräfta Stop på servern. Försök igen.'};
      }
    } finally {
      if (token === generation) { busy = false; onChange(); }
    }
  };
  return {getState, invalidate, setEventError, clearInputResults, start, run, renew,
    advance, reset, linkFault, switchFault, stop};
}
