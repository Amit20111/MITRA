import type { components } from "../../packages/contracts/api";

export type Conversation = components["schemas"]["Conversation"];
export type Message = components["schemas"]["Message"];
export type Task = components["schemas"]["Task"];
export type TaskStatus = Task["status"];
export type TaskStep = components["schemas"]["Step"];
export type ToolEvent = components["schemas"]["ToolEvent"];
export type Approval = components["schemas"]["Approval"];
export type TaskEvent = components["schemas"]["TaskEvent"];
export type Settings = components["schemas"]["Settings"];
export type RuntimeStatus = components["schemas"]["RuntimeStatus"];
export type PairingChallenge = components["schemas"]["PairingChallenge"];
export type Health = components["schemas"]["Health"];
export type Decision = components["schemas"]["Decision"];
export type SendMessage = components["schemas"]["SendMessage"];

export type MemoryInput = components["schemas"]["MemoryInput"];

export type MemoryRecord = components["schemas"]["MemoryRecord"];

export type MemoryUpdate = components["schemas"]["MemoryUpdate"];

export type DesktopJob = components["schemas"]["DesktopJob"];

export type DesktopRequest = components["schemas"]["DesktopRequest"];

export type DesktopDecision = components["schemas"]["DesktopDecision"];

export type VoiceStatus = components["schemas"]["VoiceStatus"];

export type Transcript = components["schemas"]["Transcript"];

export type SpeechAudio = components["schemas"]["SpeechAudio"];

export type BackupInfo = components["schemas"]["BackupInfo"];

export type DataStatus = components["schemas"]["DataStatus"];

export type PruneRequest = components["schemas"]["PruneRequest"];

export type PruneResult = components["schemas"]["PruneResult"];
