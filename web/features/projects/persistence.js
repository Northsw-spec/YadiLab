import {api} from '../../services/api.js';

// The serialized document is detached from the live Builder model. This module
// keeps no project, revision or SHA between calls.
export function prepareSave({filename, project, workspaceRevision, editRevision, savedName, savedSha}) {
  return Object.freeze({
    filename, workspaceRevision, editRevision,
    serializedProject: JSON.stringify(project),
    expectedSha256: savedName === filename ? savedSha : null,
  });
}

export async function saveSnapshot(request, approveConflict) {
  const submit = expectedSha256 => api('/api/save', {
    filename: request.filename,
    project: JSON.parse(request.serializedProject),
    expectedSha256,
  });
  try {
    return await submit(request.expectedSha256);
  } catch (error) {
    if (error.code !== 'CONFLICT') throw error;
    // The caller owns the live workspace and must check it before approval.
    if (!approveConflict(error)) throw error;
    if (!error.currentSha256) throw new Error('Filen ändrades eller försvann. Försök spara igen.');
    return submit(error.currentSha256);
  }
}

export function listSavedProjects() {
  return api('/api/projects');
}

export function readSavedProject(filename) {
  return api(`/api/projects/${encodeURIComponent(filename)}`);
}
