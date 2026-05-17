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
        gender: "male",
        showDeleteModal: false,
        deleteConfirmName: "",
        creationName: "",
        creationSubmitting: false,
        nameAvailability: {
            state: "idle",
            checked: "",
            available: null,
            message: "",
        },
        get creating() {
            return this.mode === "create";
        },
        get nameAvailabilityState() {
            return this.nameAvailability.state;
        },
        get creationNameStatus() {
            return this.nameAvailability.message;
        },
        normalizedCreationName() {
            return (this.creationName || "").trim();
        },
        async checkCreationNameAvailability() {
            const name = this.normalizedCreationName();
            if (!name) {
                this.nameAvailability = { state: "idle", checked: "", available: null, message: "" };
                return false;
            }
            if (name.length < 3) {
                this.nameAvailability = {
                    state: "invalid",
                    checked: name,
                    available: false,
                    message: "Минимум 3 символа",
                };
                return false;
            }
            if (name.length > 16) {
                this.nameAvailability = {
                    state: "invalid",
                    checked: name,
                    available: false,
                    message: "Максимум 16 символов",
                };
                return false;
            }
            if (this.nameAvailability.checked === name && this.nameAvailability.state !== "pending") {
                return this.nameAvailability.available === true;
            }

            this.nameAvailability = {
                state: "pending",
                checked: name,
                available: null,
                message: "Проверяем имя",
            };

            try {
                const response = await fetch(`/api/game-lobby/name-availability?name=${encodeURIComponent(name)}`, {
                    headers: { Accept: "application/json" },
                });
                if (!response.ok) throw new Error(`Name availability failed: ${response.status}`);

                const result = await response.json();
                if (this.normalizedCreationName() !== name) return false;

                const available = result.available === true;
                this.nameAvailability = {
                    state: available ? "valid" : "invalid",
                    checked: name,
                    available,
                    message: available ? "Имя свободно" : result.message || "Имя недоступно",
                };
                return available;
            } catch (error) {
                console.warn("Name availability check failed", error);
                if (this.normalizedCreationName() !== name) return false;
                this.nameAvailability = {
                    state: "invalid",
                    checked: name,
                    available: false,
                    message: "Не удалось проверить имя",
                };
                return false;
            }
        },
        async submitCreation(event) {
            const form = event.target;
            if (this.creationSubmitting) return;
            if (form.reportValidity && !form.reportValidity()) return;

            this.creationSubmitting = true;
            const available = await this.checkCreationNameAvailability();
            if (!available) {
                this.creationSubmitting = false;
                return;
            }
            form.submit();
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
