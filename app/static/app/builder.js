document.addEventListener("DOMContentLoaded", () => {
    const validationSummary = document.querySelector("#form-validation-summary");
    if (validationSummary) {
        validationSummary.focus({ preventScroll: true });
        validationSummary.scrollIntoView({ block: "center" });
    }

    const fields = document.querySelectorAll("[data-preview]");
    const source = document.querySelector("[data-resume-preview-source]");
    const pages = document.querySelector("[data-resume-preview-pages]");
    const values = new Map();
    let paginationFrame;

    const preview = (key) => source.querySelector(`[data-preview-value="${key}"]`);

    const updateText = (key, value) => {
        const target = preview(key);
        if (target) target.textContent = value;
    };

    const updatePreviewLink = (key, value) => {
        const target = preview(key);
        if (!target) return;
        if (!target.hasAttribute("data-preview-link") || !["linkedin_url", "github_url"].includes(key)) {
            target.textContent = value;
        }
        if (/^https?:\/\//i.test(value)) {
            target.href = value;
        } else {
            target.removeAttribute("href");
        }
    };

    const renderFormatted = (target, value) => {
        const marker = /(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*)/g;
        target.replaceChildren();
        let position = 0;
        for (const match of value.matchAll(marker)) {
            if (match.index > position) target.append(document.createTextNode(value.slice(position, match.index)));
            const token = match[0];
            let node = document.createTextNode(token);
            if (token.startsWith("***")) {
                node = document.createElement("strong");
                const italic = document.createElement("em");
                italic.textContent = token.slice(3, -3);
                node.append(italic);
            } else if (token.startsWith("**")) {
                node = document.createElement("strong");
                node.textContent = token.slice(2, -2);
            } else {
                node = document.createElement("em");
                node.textContent = token.slice(1, -1);
            }
            target.append(node);
            position = match.index + token.length;
        }
        if (position < value.length) target.append(document.createTextNode(value.slice(position)));
    };

    const updateMultiline = (key, value) => {
        const target = preview(key);
        if (!target) return;
        target.replaceChildren();
        const structured = ["experience", "internship_experience", "projects"].includes(key);
        let entry;
        value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((line) => {
            const bullet = /^(?:[-•]\s*|\*\s+)/.test(line);
            const text = line.replace(/^(?:[-•]\s*|\*\s+)/, "");
            if (structured) {
                if (!entry || (entry.querySelector("ul") && !bullet)) {
                    entry = document.createElement("div");
                    entry.className = "preview-entry";
                    target.append(entry);
                }
                if (bullet) {
                    let list = entry.querySelector("ul");
                    if (!list) {
                        list = document.createElement("ul");
                        entry.append(list);
                    }
                    const item = document.createElement("li");
                    renderFormatted(item, text);
                    list.append(item);
                } else {
                    const heading = document.createElement(entry.children.length ? "p" : "strong");
                    heading.className = entry.children.length ? "preview-entry-meta" : "preview-entry-title";
                    renderFormatted(heading, text);
                    entry.append(heading);
                }
                return;
            }
            const paragraph = document.createElement("p");
            paragraph.className = bullet ? "preview-line preview-line-bullet" : "preview-line";
            renderFormatted(paragraph, text);
            target.append(paragraph);
        });
    };

    const updateEducation = () => {
        const fields = ["degree", "study_stream", "university", "graduation_year", "school"];
        const parts = fields.map((key) => values.get(key) || "").filter(Boolean);
        const cgpa = values.get("cgpa_marks");
        if (cgpa) parts.push(`CGPA / Marks: ${cgpa}`);
        const target = preview("education");
        if (target) renderFormatted(target, parts.join(" | "));
    };

    const alignmentInput = document.querySelector('#profile-builder-form [name="text_alignment"]');
    const readAlignments = () => {
        if (!alignmentInput || !alignmentInput.value) return {};
        try {
            const parsed = JSON.parse(alignmentInput.value);
            return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
        } catch {
            return {};
        }
    };

    const updateVisibility = () => {
        source.querySelectorAll("[data-preview-row]").forEach((row) => {
            row.hidden = !(values.get(row.dataset.previewRow) || "").trim();
        });
        source.querySelectorAll("[data-preview-section]").forEach((section) => {
            section.hidden = !(values.get(section.dataset.previewSection) || "").trim();
        });
        source.querySelectorAll("[data-preview-group]").forEach((group) => {
            const keys = group.dataset.previewGroup.split(",");
            group.hidden = !keys.some((key) => (values.get(key) || "").trim());
        });
        const alignments = readAlignments();
        source.querySelectorAll("[data-align-field]").forEach((section) => {
            section.style.textAlign = alignments[section.dataset.alignField] || "left";
        });
    };

    const createPage = () => {
        const frame = document.createElement("div");
        frame.className = "resume-preview-frame";
        const page = document.createElement("section");
        page.className = "resume-preview-page";
        page.setAttribute("aria-label", `Resume page ${pages.children.length + 1}`);
        const content = document.createElement("div");
        content.className = "resume-preview-page-content";
        const pageNumber = document.createElement("span");
        pageNumber.className = "resume-preview-page-number";
        pageNumber.textContent = `PAGE ${pages.children.length + 1}`;
        page.append(content);
        page.append(pageNumber);
        frame.append(page);
        pages.append(frame);
        page.style.transform = `scale(${frame.clientWidth / page.offsetWidth})`;
        return content;
    };

    const pageOverflows = (page) => page.scrollHeight > page.clientHeight + 1;

    const createBlockPiece = (sourceBlock, heading) => {
        const piece = sourceBlock.cloneNode(false);
        piece.hidden = false;
        if (heading) piece.append(heading.cloneNode(true));
        return piece;
    };

    const paginate = () => {
        pages.replaceChildren();
        let currentPage = createPage();
        const blocks = [...source.querySelectorAll("[data-preview-page-block]:not([hidden])")];

        blocks.forEach((sourceBlock) => {
            const heading = [...sourceBlock.children].find((child) => child.tagName === "H3");
            const content = [...sourceBlock.children]
                .filter((child) => child !== heading && !child.hidden)
                .flatMap((child) => {
                    const alignmentField = child.dataset.alignField;
                    if (!child.classList.contains("preview-preline")) {
                        return [{ node: child, alignmentField }];
                    }
                    return [...child.children].flatMap((entry) => {
                        if (!entry.classList.contains("preview-entry")) {
                            return [{ node: entry, alignmentField }];
                        }
                        const groupTitle = [...entry.children].find((entryChild) =>
                            entryChild.classList.contains("preview-entry-title")
                        );
                        return [...entry.children].flatMap((entryChild) => {
                            const lines = entryChild.tagName === "UL" ? [...entryChild.children] : [entryChild];
                            return lines.map((node) => ({ node, alignmentField, groupTitle }));
                        });
                    });
                });
            let piece = createBlockPiece(sourceBlock, heading);
            currentPage.append(piece);

            if (pageOverflows(currentPage) && currentPage.children.length > 1) {
                piece.remove();
                currentPage = createPage();
                piece = createBlockPiece(sourceBlock, heading);
                currentPage.append(piece);
            }

            content.forEach(({ node: sourceChild, alignmentField, groupTitle }) => {
                let child = sourceChild.cloneNode(true);
                if (sourceChild.tagName === "LI") {
                    const bullet = document.createElement("p");
                    bullet.className = "preview-line preview-line-bullet";
                    bullet.replaceChildren(...[...child.childNodes]);
                    child = bullet;
                }
                if (alignmentField) {
                    child.style.textAlign = readAlignments()[alignmentField] || "left";
                }
                piece.append(child);
                if (!pageOverflows(currentPage)) return;

                child.remove();
                const pieceContentCount = piece.children.length - (heading ? 1 : 0);
                if (pieceContentCount > 0) {
                    currentPage = createPage();
                    piece = createBlockPiece(sourceBlock, heading);
                    if (sourceChild.tagName === "LI" && groupTitle) {
                        piece.append(groupTitle.cloneNode(true));
                    }
                    piece.append(child);
                    currentPage.append(piece);
                } else if (currentPage.children.length > 1) {
                    piece.remove();
                    currentPage = createPage();
                    piece = createBlockPiece(sourceBlock, heading);
                    if (sourceChild.tagName === "LI" && groupTitle) {
                        piece.append(groupTitle.cloneNode(true));
                    }
                    piece.append(child);
                    currentPage.append(piece);
                } else {
                    piece.append(child);
                }
            });
        });
    };

    const schedulePagination = () => {
        cancelAnimationFrame(paginationFrame);
        paginationFrame = requestAnimationFrame(paginate);
    };

    fields.forEach((field) => {
        const update = () => {
            const key = field.dataset.preview;
            const value = field.value.trim();
            values.set(key, value);
            if (["experience", "internship_experience", "projects", "certifications", "achievements_awards"].includes(key)) {
                updateMultiline(key, value);
            } else if (["linkedin_url", "github_url", "portfolio_url"].includes(key)) {
                updatePreviewLink(key, value);
            } else {
                const target = preview(key);
                if (target) renderFormatted(target, value);
            }
            if (["degree", "study_stream", "university", "graduation_year", "school", "cgpa_marks"].includes(key)) {
                updateEducation();
            }
            updateVisibility();
            schedulePagination();
        };
        field.addEventListener("input", update);
        update();
    });

    document.querySelectorAll(".form-section").forEach((section) => {
        const toolbar = section.querySelector("[data-text-toolbar]");
        if (!toolbar) return;
        const editableFields = [...section.querySelectorAll('[data-format-editable="true"]')];
        if (!editableFields.length) return;
        section.dataset.activeFormatField = editableFields[0].name;
        const updateAlignmentButtons = (fieldName) => {
            const selectedAlignment = readAlignments()[fieldName] || "left";
            toolbar.querySelectorAll("[data-align-action]").forEach((option) => {
                option.setAttribute("aria-pressed", String(option.dataset.alignAction === selectedAlignment));
            });
        };
        editableFields.forEach((field) => {
            field.addEventListener("focus", () => {
                section.dataset.activeFormatField = field.name;
                updateAlignmentButtons(field.name);
            });
        });
        updateAlignmentButtons(section.dataset.activeFormatField);
        toolbar.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            const field = editableFields.find((candidate) => candidate.name === section.dataset.activeFormatField);
            if (!button || !field) return;
            if (button.dataset.formatAction) {
                const start = field.selectionStart;
                const end = field.selectionEnd;
                const selected = field.value.slice(start, end);
                const marker = button.dataset.formatAction === "bold" ? "**" : "*";
                field.setRangeText(`${marker}${selected}${marker}`, start, end, "select");
                if (start === end) field.setSelectionRange(start + marker.length, start + marker.length);
                field.focus();
                field.dispatchEvent(new Event("input", { bubbles: true }));
                return;
            }
            if (button.dataset.alignAction && alignmentInput) {
                const alignments = readAlignments();
                alignments[field.name] = button.dataset.alignAction;
                alignmentInput.value = JSON.stringify(alignments);
                updateVisibility();
                schedulePagination();
                updateAlignmentButtons(field.name);
            }
        });
    });

    window.addEventListener("resize", schedulePagination);
});
