/*
 * Compiled JS — DO NOT EDIT
 * Sources: site/lobby.js, site/support.js
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
                const response = await fetch("/game-lobby/name-availability", {
                    method: "POST",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ name }),
                });
                if (!response.ok) {
                    const detail = await this.readNameAvailabilityError(response);
                    throw new Error(detail || `Name availability failed: ${response.status}`);
                }

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
                    message: error instanceof Error && error.message ? error.message : "Не удалось проверить имя",
                };
                return false;
            }
        },
        async readNameAvailabilityError(response) {
            try {
                const payload = await response.json();
                if (payload && typeof payload.detail === "string" && payload.detail) return payload.detail;
                if (payload && typeof payload.message === "string" && payload.message) return payload.message;
            } catch (error) {
                console.warn("Name availability error payload parse failed", error);
            }
            return "";
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



window.supportWizardState = function supportWizardState() {
    const categories = [
        {
            id: "bug",
            code: "BUG",
            title: "Баги",
            description: "Ошибка, поломка, зависание или неожиданное поведение.",
            feedbackType: "bug",
            question: "Это мешает продолжить игру?",
            yesNo: [
                { value: "yes", label: "Да, мешает играть" },
                { value: "no", label: "Нет, но нужно исправить" },
            ],
            places: ["Вход / аккаунт", "Лобби", "Вылазка", "Бой", "Добыча", "Инвентарь"],
            impactTitle: "Насколько серьёзно влияет?",
            impacts: ["Критично", "Блокирует действие", "Мешает, но можно обойти", "Косметика"],
            notePlaceholder: "Что вы сделали перед ошибкой и что увидели?",
        },
        {
            id: "balance",
            code: "BAL",
            title: "Баланс",
            description: "Слишком легко, слишком больно, награда не стоит риска.",
            feedbackType: "balance",
            question: "Баланс ощущается несправедливым?",
            yesNo: [
                { value: "yes", label: "Да, перекос заметный" },
                { value: "no", label: "Скорее тонкая настройка" },
            ],
            places: ["Навыки", "Монстры", "Экипировка", "Ресурсы", "Награды", "PvP / арена"],
            impactTitle: "Что именно выбивается?",
            impacts: ["Урон", "Живучесть", "Стоимость", "Редкость", "Темп прогресса", "Награда"],
            notePlaceholder: "Какой момент показался слабым или слишком сильным?",
        },
        {
            id: "combat",
            code: "TMP",
            title: "Темп боя",
            description: "Затянутость, непонятные паузы, нехватка давления или решений.",
            feedbackType: "impression",
            question: "Бой затянулся или потерял напряжение?",
            yesNo: [
                { value: "yes", label: "Да, темп просел" },
                { value: "no", label: "Нет, но есть наблюдение" },
            ],
            places: ["Начало боя", "Выбор действия", "Лог боя", "Концовка", "Смена целей", "Ожидание хода"],
            impactTitle: "Как это ощущалось?",
            impacts: ["Слишком долго", "Слишком быстро", "Мало решений", "Непонятный итог", "Не хватило риска"],
            notePlaceholder: "В какой момент бой перестал быть интересным?",
        },
        {
            id: "interface",
            code: "UI",
            title: "Интерфейс",
            description: "Непонятные кнопки, текст, состояние, навигация или адаптив.",
            feedbackType: "impression",
            question: "Было непонятно, что делать дальше?",
            yesNo: [
                { value: "yes", label: "Да, потерялся" },
                { value: "no", label: "Нет, но можно яснее" },
            ],
            places: ["Главная", "Лобби", "Экран игры", "Бой", "Инвентарь", "Мобильная версия"],
            impactTitle: "Что больше всего мешало?",
            impacts: ["Текст", "Кнопки", "Расположение", "Состояния", "Размер", "Контраст"],
            notePlaceholder: "Что вы ожидали увидеть или нажать?",
        },
        {
            id: "expeditions",
            code: "IDEA",
            title: "Идеи вылазок",
            description: "Новые события, риски, маршруты, находки и цели за стеной.",
            feedbackType: "wish",
            question: "Идея связана с новым игровым контентом?",
            yesNo: [
                { value: "yes", label: "Да, это контент" },
                { value: "no", label: "Нет, скорее улучшение" },
            ],
            places: ["Разлом", "Внешний город", "Маршрут", "Добыча", "Событие", "Возвращение"],
            impactTitle: "Куда это лучше добавить?",
            impacts: ["Короткая вылазка", "Редкое событие", "Опасная зона", "Награда", "Социальный момент"],
            notePlaceholder: "Опишите идею коротко: цель, риск, награда.",
        },
        {
            id: "general",
            code: "GEN",
            title: "Общий вопрос",
            description: "Доступ, аккаунт, вход в игру или вопрос не из других разделов.",
            feedbackType: "wish",
            question: "Вопрос мешает начать или продолжить игру?",
            yesNo: [
                { value: "yes", label: "Да, мешает" },
                { value: "no", label: "Нет, просто вопрос" },
            ],
            places: ["Регистрация", "Вход", "Аккаунт", "Лобби", "Запуск игры", "Другое"],
            impactTitle: "Что нужно уточнить?",
            impacts: ["Не могу войти", "Не вижу персонажа", "Не понимаю следующий шаг", "Нужна подсказка", "Другое"],
            notePlaceholder: "Опишите вопрос или место, где остановились.",
        },
    ];

    return {
        categories,
        selectedCategory: "bug",
        step: 0,
        answers: {
            intent: "",
            place: "",
            customPlace: "",
            impact: "",
            note: "",
        },
        get currentCategory() {
            return this.categories.find((item) => item.id === this.selectedCategory) || this.categories[0];
        },
        get selectedIntentLabel() {
            const selected = this.currentCategory.yesNo.find((item) => item.value === this.answers.intent);
            return selected ? selected.label : "Не выбрано";
        },
        get resolvedPlace() {
            return this.answers.customPlace.trim() || this.answers.place || "Не выбрано";
        },
        get submitHref() {
            return `/account/feedback/new?type=${encodeURIComponent(this.currentCategory.feedbackType)}`;
        },
        selectCategory(categoryId) {
            this.selectedCategory = categoryId;
            this.step = 0;
            this.answers = {
                intent: "",
                place: "",
                customPlace: "",
                impact: "",
                note: "",
            };
        },
        nextStep() {
            if (this.step < 3) this.step += 1;
        },
        prevStep() {
            if (this.step > 0) this.step -= 1;
        },
    };
};
