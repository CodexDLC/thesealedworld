/*
 * Compiled JS — DO NOT EDIT
 * Sources: site/lobby.js
 * Minified: False
 */


window.lobbyPanelState = function lobbyPanelState(initialMode, initialSelection) {
    const selection = initialSelection || {};
    return {
        selectedSlot: selection.selectedSlot ?? null,
        selectedEmpty: selection.selectedEmpty ?? false,
        selectedCharacterId: selection.selectedCharacterId ?? "",
        selectedName: selection.selectedName ?? "",
        mode: initialMode || "intro",
        showDeleteModal: false,
        deleteConfirmName: "",
        get creating() {
            return this.mode === "create";
        },
        confirmDelete() {
            if (!this.selectedCharacterId || this.selectedEmpty) return;
            this.showDeleteModal = true;
            this.deleteConfirmName = "";
            this.$nextTick(() => {
                this.$refs.modalInput.focus();
            });
        },
        submitDelete() {
            if (this.deleteConfirmName.trim() !== this.selectedName) {
                alert("Имя не совпало. Персонаж не удален.");
                return;
            }
            this.$refs.confirmName.value = this.deleteConfirmName.trim();
            this.$refs.deleteForm.submit();
        },
    };
};
