# Knowledge Base Segregation & Seamless Media Integration

This plan implements the requested separation between the "Training" and "Media Library" functions within the Knowledge page, and introduces a frictionless media referencing workflow directly into the Agentic Hub chat interface.

## User Review Required

> [!IMPORTANT]
> **Asset Referencing Payload:** When referencing a media asset in the chat, the frontend will attach the asset's URI/ID to the backend payload. Please confirm if modifying the `/api/chat/stream` `context` object to include `{ "attached_media": [asset_id] }` aligns with your backend processing logic.

## Proposed Changes

---

### 1. Segregating Knowledge & Training
The current `frontend/src/app/knowledge/page.tsx` unifies media and documents. We will restructure this page to have two distinct main components logically separated: **Training** and **Media Library**.

#### [MODIFY] `frontend/src/app/knowledge/page.tsx`
- **Tab/Mode Split:** Create primary tabs/modes for **"Training"** (vectorizing standard files like CSV, Excel, PDF, URLs) and **"Media Library"** (storage for raw assets like Banners, Images, Video).
- **Training Tab:** Includes the drop zone specifically configured for documents, URLs, and Notes. Uploads here route to the vector database.
- **Media Library Tab:** Displays a rich visual grid for assets with an integrated upload button strictly for visual/audio media. 

### 2. Agentic Hub Chat Additions
We will add a mechanism to easily reference and upload assets directly from the chat screen without breaking the user's flow.

#### [MODIFY] `frontend/src/app/chat/page.tsx`
- **New `+` Button:** Inject a `lucide-react` Plus icon button into the left side of the bottom input bar (opposite the Send button).
- **Asset Preview Popover/Modal:** Clicking `+` will toggle an `AssetSelector` overlay. This overlay will fetch and map over `api.media.list()` to show visual thumbnails of existing Media Library assets.
- **Seamless Upload:** Include an "Upload New" button inside this preview. Clicking it opens the native file picker, uploads the new media silently via `api.media.upload()`, and auto-selects it so it is ready to be sent.
- **Message Input State:** Add an `attachedMedia` state array. Selecting an asset from the preview will render a chip or thumbnail above the textarea. When the user clicks "Send", the `asset.id` and `asset.public_url` will be forwarded to the backend context.

#### [NEW] `frontend/src/components/chat/AssetSelector.tsx` (Optional)
- We may extract the media fetching grid and upload logic into a clean child component to keep `page.tsx` maintainable if it gets too large.

---

## Open Questions

- **Vectorizing Excel/CSV:** Does your existing `api.training.upload` backend endpoint natively support parsing `.xlsx` and `.csv` right now, or should we filter the accepted file types for now?
- **Referenced Asset Display:** When the AI agent replies, should it also render the image/video if it utilizes the asset you referenced, or should only your prompt show the thumbnail?

## Verification Plan

### Automated Tests
- Ensure `AssetSelector` loads without breaking the chat stream pipeline.

### Manual Verification
1. Navigate to the "Knowledge" page and ensure the "Training" layout clearly differs from the "Media Library" layout.
2. In the "Training" tab, verify that documents/text/links are prioritized.
3. Navigate to "Agentic Hub", click `+`, upload a banner seamlessly, click the uploaded banner, and type a prompt. Verify the UI correctly queues the banner and passes it to the AI.
