// Generated from apps/api Pydantic contracts. Do not edit.
export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Settings */
        get: operations["settings_api_v1_settings_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runtime */
        get: operations["runtime_api_v1_runtime_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/pairing": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Begin Pairing */
        post: operations["begin_pairing_api_v1_runtime_pairing_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/pairing/claim": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Claim Pairing */
        post: operations["claim_pairing_api_v1_runtime_pairing_claim_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/{identity}/heartbeat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Runtime Heartbeat */
        post: operations["runtime_heartbeat_api_v1_runtime__identity__heartbeat_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/{identity}/disconnect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Runtime Disconnect */
        post: operations["runtime_disconnect_api_v1_runtime__identity__disconnect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Runtime Revoke */
        post: operations["runtime_revoke_api_v1_runtime_revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runtime History */
        get: operations["runtime_history_api_v1_runtime_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/voice/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Voice Status */
        get: operations["voice_status_api_v1_voice_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/voice/transcribe": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Voice Transcribe */
        post: operations["voice_transcribe_api_v1_voice_transcribe_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/voice/speak": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Voice Speak */
        post: operations["voice_speak_api_v1_voice_speak_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/memories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Memory List */
        get: operations["memory_list_api_v1_memories_get"];
        put?: never;
        /** Memory Create */
        post: operations["memory_create_api_v1_memories_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/memories/{identity}/update": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Memory Update */
        post: operations["memory_update_api_v1_memories__identity__update_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/memories/{identity}/delete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Memory Delete */
        post: operations["memory_delete_api_v1_memories__identity__delete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/desktop/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Desktop Jobs */
        get: operations["desktop_jobs_api_v1_runtime_desktop_jobs_get"];
        put?: never;
        /** Desktop Create */
        post: operations["desktop_create_api_v1_runtime_desktop_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/desktop/{identity}/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Desktop Image */
        get: operations["desktop_image_api_v1_runtime_desktop__identity__image_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/desktop/{identity}/decision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Decide */
        post: operations["desktop_decide_api_v1_runtime_desktop__identity__decision_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/desktop/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Stop */
        post: operations["desktop_stop_api_v1_runtime_desktop_stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/desktop/enable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Enable */
        post: operations["desktop_enable_api_v1_runtime_desktop_enable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/{runtime_id}/poll": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Poll */
        post: operations["desktop_poll_api_v1_runtime__runtime_id__poll_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/{runtime_id}/{identity}/authorize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Authorize */
        post: operations["desktop_authorize_api_v1_runtime__runtime_id___identity__authorize_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime/{runtime_id}/{identity}/result": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Desktop Result */
        post: operations["desktop_result_api_v1_runtime__runtime_id___identity__result_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Conversations */
        get: operations["list_conversations_api_v1_conversations_get"];
        put?: never;
        /** Create Conversation */
        post: operations["create_conversation_api_v1_conversations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{identity}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Conversation */
        get: operations["conversation_api_v1_conversations__identity__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{identity}/rename": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rename Conversation */
        post: operations["rename_conversation_api_v1_conversations__identity__rename_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{identity}/delete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Delete Conversation */
        post: operations["delete_conversation_api_v1_conversations__identity__delete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/data/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Data Status */
        get: operations["get_data_status_api_v1_data_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/data/backup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Data Backup */
        post: operations["create_data_backup_api_v1_data_backup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/data/prune": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Prune Data */
        post: operations["prune_data_api_v1_data_prune_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/data/diagnostics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download Diagnostics */
        get: operations["download_diagnostics_api_v1_data_diagnostics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{identity}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Message */
        post: operations["message_api_v1_conversations__identity__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tasks */
        get: operations["list_tasks_api_v1_tasks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{identity}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Task */
        get: operations["task_api_v1_tasks__identity__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/approvals/pending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pending */
        get: operations["pending_api_v1_approvals_pending_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/approvals/{identity}/decision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide */
        post: operations["decide_api_v1_approvals__identity__decision_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{identity}/{action}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Control */
        post: operations["control_api_v1_tasks__identity___action__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{identity}/events/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** History */
        get: operations["history_api_v1_tasks__identity__events_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{identity}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_api_v1_tasks__identity__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Approval */
        Approval: {
            /** Id */
            id: string;
            /** Taskid */
            taskId: string;
            /** Stepid */
            stepId: string;
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "approved" | "rejected" | "expired";
            /** Target */
            target: string;
            /** Action */
            action: string;
            /**
             * Risk
             * @default high
             * @constant
             */
            risk: "high";
            /** Expiresat */
            expiresAt: string;
            /** Digest */
            digest: string;
        };
        /** BackupInfo */
        BackupInfo: {
            /** Filename */
            filename: string;
            /** Sizebytes */
            sizeBytes: number;
            /** Createdat */
            createdAt: string;
        };
        /** Conversation */
        Conversation: {
            /** Id */
            id: string;
            /**
             * Title
             * @default New conversation
             */
            title: string;
            /** Messages */
            messages: components["schemas"]["Message"][];
            task: components["schemas"]["Task"] | null;
        };
        /** ConversationRename */
        ConversationRename: {
            /** Title */
            title: string;
        };
        /** DataStatus */
        DataStatus: {
            /** Databasepath */
            databasePath: string;
            /** Sizebytes */
            sizeBytes: number;
            /** Alembicrevision */
            alembicRevision: string;
            /** Conversations */
            conversations: number;
            /** Tasks */
            tasks: number;
            /** Events */
            events: number;
            /** Traces */
            traces: number;
            /** Memories */
            memories: number;
            /** Backups */
            backups: components["schemas"]["BackupInfo"][];
        };
        /** Decision */
        Decision: {
            /**
             * Taskid
             * Format: uuid
             */
            taskId: string;
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "reject";
            /** Digest */
            digest: string;
        };
        /** DesktopDecision */
        DesktopDecision: {
            /** Digest */
            digest: string;
            /** Approve */
            approve: boolean;
        };
        /** DesktopJob */
        DesktopJob: {
            /**
             * Hasimage
             * @default false
             */
            hasImage: boolean;
            /** Id */
            id: string;
            /** Runtimeid */
            runtimeId: string;
            /**
             * Action
             * @enum {string}
             */
            action: "list_windows" | "screenshot" | "focus";
            /** Targetid */
            targetId: string | null;
            /**
             * Targettitle
             * @default Visible windows
             */
            targetTitle: string;
            /** Digest */
            digest: string;
            /** Expiresat */
            expiresAt: string;
            /**
             * State
             * @default pending
             * @enum {string}
             */
            state: "pending" | "approved" | "dispatched" | "completed" | "failed" | "cancelled";
            /**
             * Message
             * @default Review the exact operation before approval.
             */
            message: string;
            /** Targets */
            targets: components["schemas"]["DesktopTarget"][];
            /** Image */
            image: string | null;
        };
        /** DesktopRequest */
        DesktopRequest: {
            /**
             * Action
             * @enum {string}
             */
            action: "list_windows" | "screenshot" | "focus";
            /** Targetid */
            targetId?: string | null;
        };
        /** DesktopResult */
        DesktopResult: {
            /** Success */
            success: boolean;
            /** Message */
            message: string;
            /** Targets */
            targets?: components["schemas"]["DesktopTarget"][];
            /** Image */
            image?: string | null;
        };
        /** DesktopTarget */
        DesktopTarget: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Processid */
            processId: number;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Health */
        Health: {
            /**
             * Status
             * @default ok
             */
            status: string;
            /** Provider */
            provider: string;
            /** Model */
            model: string;
            /**
             * Mode
             * @default local
             */
            mode: string;
        };
        /** MemoryInput */
        MemoryInput: {
            /** Key */
            key: string;
            /** Content */
            content: string;
            /** Conversationid */
            conversationId?: string | null;
            /**
             * Confirmed
             * @default true
             */
            confirmed: boolean;
        };
        /** MemoryRecord */
        MemoryRecord: {
            /** Key */
            key: string;
            /** Content */
            content: string;
            /** Conversationid */
            conversationId: string | null;
            /**
             * Confirmed
             * @default true
             */
            confirmed: boolean;
            /** Id */
            id: string;
            /**
             * Source
             * @default user
             * @constant
             */
            source: "user";
            /** Createdat */
            createdAt: string;
            /** Updatedat */
            updatedAt: string;
            /**
             * Revision
             * @default 1
             */
            revision: number;
        };
        /** MemoryUpdate */
        MemoryUpdate: {
            /** Key */
            key: string;
            /** Content */
            content: string;
            /** Conversationid */
            conversationId?: string | null;
            /**
             * Confirmed
             * @default true
             */
            confirmed: boolean;
            /** Revision */
            revision: number;
        };
        /** Message */
        Message: {
            /** Id */
            id: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "assistant";
            /** Content */
            content: string;
            /** Createdat */
            createdAt: string;
        };
        /** PairingChallenge */
        PairingChallenge: {
            /** Pairingid */
            pairingId: string;
            /** Pairingcode */
            pairingCode: string;
            /** Expiresat */
            expiresAt: string;
        };
        /** PairingClaim */
        PairingClaim: {
            /**
             * Pairingid
             * Format: uuid
             */
            pairingId: string;
            /** Code */
            code: string;
            /** Name */
            name: string;
            /**
             * Platform
             * @default windows
             * @constant
             */
            platform: "windows";
            /**
             * Protocolversion
             * @default 1
             * @constant
             */
            protocolVersion: 1;
        };
        /** PruneRequest */
        PruneRequest: {
            /**
             * Days
             * @default 30
             */
            days: number;
        };
        /** PruneResult */
        PruneResult: {
            /** Deletedevents */
            deletedEvents: number;
            /** Deletedtraces */
            deletedTraces: number;
        };
        /** RoleConfig */
        RoleConfig: {
            /**
             * Provider
             * @default local
             * @enum {string}
             */
            provider: "local" | "hosted";
            /** Baseurl */
            baseUrl: string;
            /** Model */
            model: string;
            /** Configured */
            configured: boolean;
            /**
             * Implemented
             * @default false
             */
            implemented: boolean;
        };
        /** RuntimeAudit */
        RuntimeAudit: {
            /** Id */
            id: number;
            /** Event */
            event: string;
            /** Runtimeid */
            runtimeId: string | null;
            /** Timestamp */
            timestamp: string;
        };
        /** RuntimeCredential */
        RuntimeCredential: {
            /** Runtimeid */
            runtimeId: string;
            /** Token */
            token: string;
            /** Expiresat */
            expiresAt: string;
            /**
             * Heartbeatseconds
             * @default 5
             */
            heartbeatSeconds: number;
        };
        /** RuntimeHeartbeat */
        RuntimeHeartbeat: {
            /**
             * Protocolversion
             * @default 1
             * @constant
             */
            protocolVersion: 1;
            /**
             * Runtimeversion
             * @default 0.1.0
             * @constant
             */
            runtimeVersion: "0.1.0";
            /**
             * Desktopenabled
             * @default false
             */
            desktopEnabled: boolean;
        };
        /** RuntimeRevoke */
        RuntimeRevoke: {
            /**
             * Runtimeid
             * Format: uuid
             */
            runtimeId: string;
        };
        /** RuntimeStatus */
        RuntimeStatus: {
            /**
             * Connected
             * @default false
             */
            connected: boolean;
            /**
             * Paired
             * @default false
             */
            paired: boolean;
            /** Runtimeid */
            runtimeId: string | null;
            /** Name */
            name: string | null;
            /** Lastseen */
            lastSeen: string | null;
            /** Credentialexpiresat */
            credentialExpiresAt: string | null;
            /**
             * Leaseseconds
             * @default 15
             */
            leaseSeconds: number;
            /** Capabilities */
            capabilities: string[];
            /**
             * Message
             * @default No Windows runtime paired.
             */
            message: string;
        };
        /** SendMessage */
        SendMessage: {
            /** Content */
            content: string;
            /**
             * Requestid
             * Format: uuid
             */
            requestId: string;
        };
        /** Settings */
        Settings: {
            /**
             * Browserinteraction
             * @default false
             */
            browserInteraction: boolean;
            /**
             * Browserenabled
             * @default false
             */
            browserEnabled: boolean;
            /** Browserorigins */
            browserOrigins: string[];
            /** Roles */
            roles: {
                [key: string]: components["schemas"]["RoleConfig"];
            };
            /** Workspace */
            workspace: string;
            /** Maxsteps */
            maxSteps: number;
            /** Retries */
            retries: number;
            /** Approvalseconds */
            approvalSeconds: number;
            /** Thinking */
            thinking: boolean;
            /**
             * Localruntime
             * @default not connected
             */
            localRuntime: string;
        };
        /** SpeechAudio */
        SpeechAudio: {
            /** Audio */
            audio: string;
            /**
             * Mime
             * @default audio/mpeg
             * @constant
             */
            mime: "audio/mpeg";
        };
        /** SpeechInput */
        SpeechInput: {
            /** Text */
            text: string;
        };
        /** Step */
        Step: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Tool */
            tool: string;
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "attempted" | "succeeded" | "failed" | "verified";
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Arguments */
            arguments: {
                [key: string]: unknown;
            };
            /** Result */
            result: {
                [key: string]: unknown;
            } | null;
            /** Verification */
            verification: string | null;
        };
        /** Task */
        Task: {
            /** Id */
            id: string;
            /** Conversationid */
            conversationId: string;
            /** Title */
            title: string;
            /**
             * Status
             * @default queued
             * @enum {string}
             */
            status: "queued" | "planning" | "awaiting_approval" | "running" | "verifying" | "completed" | "failed" | "cancelled" | "needs_user_input" | "paused";
            /** Steps */
            steps: components["schemas"]["Step"][];
            /** Events */
            events: components["schemas"]["ToolEvent"][];
            approval: components["schemas"]["Approval"] | null;
            /** Summary */
            summary: string | null;
            /** Draft */
            draft: string | null;
            /** Provider */
            provider: string;
            /** Model */
            model: string;
            /** Messageid */
            messageId: string;
            /** Outline */
            outline: string[];
            /**
             * Iterations
             * @default 0
             */
            iterations: number;
            /** Resumestate */
            resumeState: ("queued" | "planning" | "awaiting_approval" | "running" | "verifying" | "completed" | "failed" | "cancelled" | "needs_user_input" | "paused") | null;
        };
        /** TaskEvent */
        TaskEvent: {
            /** Id */
            id: number;
            /**
             * Type
             * @enum {string}
             */
            type: "message.created" | "message.delta" | "task.created" | "task.status_changed" | "plan.created" | "step.started" | "approval.requested" | "approval.decided" | "tool.started" | "tool.completed" | "tool.failed" | "step.verified" | "task.completed" | "task.failed" | "task.cancelled";
            /** Taskid */
            taskId: string;
            /** Conversationid */
            conversationId: string;
            /** Timestamp */
            timestamp: string;
            payload: components["schemas"]["Task"];
            /** Delta */
            delta: string | null;
        };
        /** ToolEvent */
        ToolEvent: {
            /** Id */
            id: string;
            /** Tool */
            tool: string;
            /** Input */
            input: string;
            /** Output */
            output: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "attempted" | "succeeded" | "failed" | "verified";
            /** Createdat */
            createdAt: string;
        };
        /** Transcript */
        Transcript: {
            /** Text */
            text: string;
            /**
             * Reviewrequired
             * @default true
             */
            reviewRequired: boolean;
        };
        /** TranscriptionInput */
        TranscriptionInput: {
            /** Audio */
            audio: string;
            /**
             * Mime
             * @enum {string}
             */
            mime: "audio/webm" | "audio/ogg" | "audio/wav" | "audio/mp4";
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** VoiceStatus */
        VoiceStatus: {
            /** Enabled */
            enabled: boolean;
            /** Transcription */
            transcription: boolean;
            /** Speech */
            speech: boolean;
            /** Message */
            message: string;
            /**
             * Maxrecordingseconds
             * @default 30
             */
            maxRecordingSeconds: number;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
        };
    };
    settings_api_v1_settings_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Settings"];
                };
            };
        };
    };
    runtime_api_v1_runtime_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeStatus"];
                };
            };
        };
    };
    begin_pairing_api_v1_runtime_pairing_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PairingChallenge"];
                };
            };
        };
    };
    claim_pairing_api_v1_runtime_pairing_claim_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PairingClaim"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeCredential"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    runtime_heartbeat_api_v1_runtime__identity__heartbeat_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RuntimeHeartbeat"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeStatus"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    runtime_disconnect_api_v1_runtime__identity__disconnect_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeStatus"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    runtime_revoke_api_v1_runtime_revoke_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RuntimeRevoke"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeStatus"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    runtime_history_api_v1_runtime_audit_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeAudit"][];
                };
            };
        };
    };
    voice_status_api_v1_voice_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VoiceStatus"];
                };
            };
        };
    };
    voice_transcribe_api_v1_voice_transcribe_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TranscriptionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Transcript"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    voice_speak_api_v1_voice_speak_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SpeechInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SpeechAudio"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    memory_list_api_v1_memories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryRecord"][];
                };
            };
        };
    };
    memory_create_api_v1_memories_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoryInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryRecord"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    memory_update_api_v1_memories__identity__update_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoryUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryRecord"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    memory_delete_api_v1_memories__identity__delete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryRecord"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_jobs_api_v1_runtime_desktop_jobs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"][];
                };
            };
        };
    };
    desktop_create_api_v1_runtime_desktop_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DesktopRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_image_api_v1_runtime_desktop__identity__image_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_decide_api_v1_runtime_desktop__identity__decision_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DesktopDecision"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_stop_api_v1_runtime_desktop_stop_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"][];
                };
            };
        };
    };
    desktop_enable_api_v1_runtime_desktop_enable_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"][];
                };
            };
        };
    };
    desktop_poll_api_v1_runtime__runtime_id__poll_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                runtime_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_authorize_api_v1_runtime__runtime_id___identity__authorize_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                runtime_id: string;
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desktop_result_api_v1_runtime__runtime_id___identity__result_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                runtime_id: string;
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DesktopResult"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesktopJob"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_conversations_api_v1_conversations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"][];
                };
            };
        };
    };
    create_conversation_api_v1_conversations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"];
                };
            };
        };
    };
    conversation_api_v1_conversations__identity__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rename_conversation_api_v1_conversations__identity__rename_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationRename"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_conversation_api_v1_conversations__identity__delete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_data_status_api_v1_data_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DataStatus"];
                };
            };
        };
    };
    create_data_backup_api_v1_data_backup_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackupInfo"];
                };
            };
        };
    };
    prune_data_api_v1_data_prune_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PruneRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PruneResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_diagnostics_api_v1_data_diagnostics_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    message_api_v1_conversations__identity__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SendMessage"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Conversation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_tasks_api_v1_tasks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Task"][];
                };
            };
        };
    };
    task_api_v1_tasks__identity__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Task"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pending_api_v1_approvals_pending_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Approval"][];
                };
            };
        };
    };
    decide_api_v1_approvals__identity__decision_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Decision"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Task"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    control_api_v1_tasks__identity___action__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identity: string;
                action: "pause" | "resume" | "cancel";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Task"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    history_api_v1_tasks__identity__events_history_get: {
        parameters: {
            query?: {
                after?: number;
            };
            header?: never;
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskEvent"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    events_api_v1_tasks__identity__events_get: {
        parameters: {
            query?: {
                after?: number;
            };
            header?: {
                "last-event-id"?: string | null;
            };
            path: {
                identity: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
