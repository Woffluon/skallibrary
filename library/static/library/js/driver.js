/*!
 * Driver.js v1.3.1 (MIT License)
 * Standalone, lightweight, accessible tour engine for web interfaces.
 * Tailored for SKAL Library Management System.
 */
(function (global, factory) {
  if (typeof exports === 'object' && typeof module !== 'undefined') {
    module.exports = factory();
  } else if (typeof define === 'function' && define.amd) {
    define(factory);
  } else {
    var instance = factory();
    global = typeof globalThis !== 'undefined' ? globalThis : global || self;
    global.driver = instance;
    global.driver.js = instance;
    global.Driver = instance.driver;
  }
})(this, function () {
  'use strict';

  var prefersReducedMotion = function () {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  };

  function clamp(val, min, max) {
    return Math.max(min, Math.min(val, max));
  }

  function getElement(selectorOrElement) {
    if (!selectorOrElement) return null;
    if (typeof selectorOrElement === 'string') {
      try {
        return document.querySelector(selectorOrElement);
      } catch (e) {
        return null;
      }
    }
    if (selectorOrElement instanceof HTMLElement) {
      return selectorOrElement;
    }
    return null;
  }

  var defaultOptions = {
    steps: [],
    animate: true,
    overlayColor: 'rgba(15, 23, 42, 0.65)',
    stagePadding: 8,
    stageRadius: 6,
    allowClose: true,
    overlayClickNext: false,
    showProgress: true,
    progressText: '{{current}} / {{total}}',
    nextBtnText: 'İleri',
    prevBtnText: 'Geri',
    doneBtnText: 'Tamamla',
    closeBtnText: 'Kapat',
    showButtons: ['next', 'previous', 'close'],
    popoverClass: '',
    onHighlightStarted: null,
    onHighlighted: null,
    onDestroyed: null,
    onNextClick: null,
    onPrevClick: null,
    onCloseClick: null,
    onPopoverRender: null,
  };

  function createDriver(userOptions) {
    var config = Object.assign({}, defaultOptions, userOptions || {});
    var activeIndex = -1;
    var activeElement = null;
    var isActivated = false;
    var lastFocusedElement = null;

    // DOM References
    var overlaySvg = null;
    var overlayPath = null;
    var stageEl = null;
    var popoverEl = null;

    var resizeRafId = null;

    function buildSvgOverlay() {
      if (overlaySvg) return;

      overlaySvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      overlaySvg.setAttribute('class', 'driver-overlay');
      overlaySvg.setAttribute('aria-hidden', 'true');
      overlaySvg.style.position = 'fixed';
      overlaySvg.style.top = '0';
      overlaySvg.style.left = '0';
      overlaySvg.style.width = '100vw';
      overlaySvg.style.height = '100vh';
      overlaySvg.style.pointerEvents = 'auto';
      overlaySvg.style.zIndex = '100000';
      overlaySvg.style.overflow = 'hidden';

      overlayPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      overlayPath.setAttribute('class', 'driver-overlay-path');
      overlayPath.setAttribute('fill-rule', 'evenodd');
      overlayPath.setAttribute('fill', config.overlayColor);
      overlayPath.style.transition = (!prefersReducedMotion() && config.animate)
        ? 'd 0.25s cubic-bezier(0.4, 0, 0.2, 1)'
        : 'none';

      overlaySvg.appendChild(overlayPath);
      document.body.appendChild(overlaySvg);

      overlaySvg.addEventListener('click', function (e) {
        if (e.target !== overlaySvg && e.target !== overlayPath) return;
        if (config.overlayClickNext) {
          moveNext();
        } else if (config.allowClose) {
          destroy();
        }
      });
    }

    function buildStage() {
      if (stageEl) return;
      stageEl = document.createElement('div');
      stageEl.className = 'driver-stage';
      stageEl.setAttribute('aria-hidden', 'true');
      stageEl.style.position = 'fixed';
      stageEl.style.pointerEvents = 'none';
      stageEl.style.zIndex = '100001';
      stageEl.style.borderRadius = config.stageRadius + 'px';
      stageEl.style.boxSizing = 'border-box';
      stageEl.style.transition = (!prefersReducedMotion() && config.animate)
        ? 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)'
        : 'none';
      document.body.appendChild(stageEl);
    }

    function buildPopover() {
      if (popoverEl) return;

      popoverEl = document.createElement('div');
      popoverEl.className = 'driver-popover ' + (config.popoverClass || '');
      popoverEl.setAttribute('role', 'dialog');
      popoverEl.setAttribute('aria-modal', 'true');
      popoverEl.setAttribute('aria-labelledby', 'driver-popover-title');
      popoverEl.setAttribute('aria-describedby', 'driver-popover-desc');
      popoverEl.style.position = 'fixed';
      popoverEl.style.zIndex = '100002';
      popoverEl.style.boxSizing = 'border-box';
      popoverEl.style.transition = (!prefersReducedMotion() && config.animate)
        ? 'transform 0.2s ease, opacity 0.2s ease'
        : 'none';

      popoverEl.innerHTML = [
        '<div class="driver-popover-arrow" aria-hidden="true"></div>',
        '<div class="driver-popover-header">',
        '  <h3 class="driver-popover-title" id="driver-popover-title"></h3>',
        '  <button type="button" class="driver-popover-close-btn" aria-label="Rehberi Kapat">',
        '    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="2" y1="2" x2="12" y2="12"></line><line x1="12" y1="2" x2="2" y2="12"></line></svg>',
        '  </button>',
        '</div>',
        '<div class="driver-popover-description" id="driver-popover-desc"></div>',
        '<div class="driver-popover-footer">',
        '  <span class="driver-popover-progress-text" aria-live="polite"></span>',
        '  <div class="driver-popover-navigation-btns">',
        '    <button type="button" class="driver-popover-btn driver-popover-prev-btn"></button>',
        '    <button type="button" class="driver-popover-btn driver-popover-next-btn"></button>',
        '  </div>',
        '</div>',
      ].join('');

      document.body.appendChild(popoverEl);

      // Event Listeners on Popover Buttons
      var closeBtn = popoverEl.querySelector('.driver-popover-close-btn');
      var prevBtn = popoverEl.querySelector('.driver-popover-prev-btn');
      var nextBtn = popoverEl.querySelector('.driver-popover-next-btn');

      closeBtn.addEventListener('click', function () {
        if (typeof config.onCloseClick === 'function') {
          config.onCloseClick(getActiveElement(), getActiveStep(), {
            config: config,
            state: { activeIndex: activeIndex },
          });
        }
        destroy();
      });

      prevBtn.addEventListener('click', function () {
        if (typeof config.onPrevClick === 'function') {
          config.onPrevClick(getActiveElement(), getActiveStep(), {
            config: config,
            state: { activeIndex: activeIndex },
          });
        }
        movePrevious();
      });

      nextBtn.addEventListener('click', function () {
        if (typeof config.onNextClick === 'function') {
          config.onNextClick(getActiveElement(), getActiveStep(), {
            config: config,
            state: { activeIndex: activeIndex },
          });
        }
        if (isLastStep()) {
          destroy();
        } else {
          moveNext();
        }
      });
    }

    function calculateCutoutPath(rect, radius) {
      var w = window.innerWidth;
      var h = window.innerHeight;

      // Base veil covering full viewport
      var outer = 'M 0 0 h ' + w + ' v ' + h + ' h -' + w + ' Z';

      if (!rect) {
        return outer;
      }

      var x = rect.left;
      var y = rect.top;
      var rw = rect.width;
      var rh = rect.height;
      var r = Math.min(radius, rw / 2, rh / 2);

      // Rounded rectangle cutout drawn counter-clockwise with fill-rule="evenodd"
      var cutout = [
        'M ' + (x + r) + ' ' + y,
        'h ' + (rw - 2 * r),
        'a ' + r + ' ' + r + ' 0 0 1 ' + r + ' ' + r,
        'v ' + (rh - 2 * r),
        'a ' + r + ' ' + r + ' 0 0 1 -' + r + ' ' + r,
        'h -' + (rw - 2 * r),
        'a ' + r + ' ' + r + ' 0 0 1 -' + r + ' -' + r,
        'v -' + (rh - 2 * r),
        'a ' + r + ' ' + r + ' 0 0 1 ' + r + ' -' + r,
        'Z',
      ].join(' ');

      return outer + ' ' + cutout;
    }

    function positionElements(targetEl, popoverConfig) {
      if (!isActivated || !popoverEl) return;

      var winW = window.innerWidth;
      var winH = window.innerHeight;
      var padding = config.stagePadding || 8;
      var radius = config.stageRadius || 6;

      var targetRect = null;
      if (targetEl && targetEl.getBoundingClientRect) {
        var rawRect = targetEl.getBoundingClientRect();
        // If element is actually rendered in DOM
        if (rawRect.width > 0 && rawRect.height > 0) {
          targetRect = {
            top: Math.max(0, rawRect.top - padding),
            left: Math.max(0, rawRect.left - padding),
            width: rawRect.width + padding * 2,
            height: rawRect.height + padding * 2,
          };
          targetRect.right = targetRect.left + targetRect.width;
          targetRect.bottom = targetRect.top + targetRect.height;
        }
      }

      // 1. Update SVG Cutout Overlay
      if (overlayPath) {
        var pathData = calculateCutoutPath(targetRect, radius);
        overlayPath.setAttribute('d', pathData);
      }

      // 2. Update Stage Element
      if (stageEl) {
        if (targetRect) {
          stageEl.style.display = 'block';
          stageEl.style.top = targetRect.top + 'px';
          stageEl.style.left = targetRect.left + 'px';
          stageEl.style.width = targetRect.width + 'px';
          stageEl.style.height = targetRect.height + 'px';
        } else {
          stageEl.style.display = 'none';
        }
      }

      // 3. Position Popover
      popoverEl.style.visibility = 'hidden';
      popoverEl.style.display = 'flex';
      var popRect = popoverEl.getBoundingClientRect();

      var popW = popRect.width || 340;
      var popH = popRect.height || 180;
      var arrowEl = popoverEl.querySelector('.driver-popover-arrow');

      if (!targetRect) {
        // Centered Modal when no target element
        var centerTop = clamp((winH - popH) / 2, 16, winH - popH - 16);
        var centerLeft = clamp((winW - popW) / 2, 16, winW - popW - 16);
        popoverEl.style.top = centerTop + 'px';
        popoverEl.style.left = centerLeft + 'px';
        popoverEl.setAttribute('data-side', 'center');
        if (arrowEl) arrowEl.style.display = 'none';
        popoverEl.style.visibility = 'visible';
        return;
      }

      if (arrowEl) arrowEl.style.display = 'block';

      var requestedSide = (popoverConfig && popoverConfig.side) || 'bottom';
      var side = requestedSide;
      var margin = 14;
      var popTop = 0;
      var popLeft = 0;

      // Smart flip logic if overflow
      if (side === 'bottom' && targetRect.bottom + popH + margin > winH) {
        side = 'top';
      } else if (side === 'top' && targetRect.top - popH - margin < 0) {
        side = 'bottom';
      } else if (side === 'right' && targetRect.right + popW + margin > winW) {
        side = 'left';
      } else if (side === 'left' && targetRect.left - popW - margin < 0) {
        side = 'right';
      }

      if (side === 'bottom') {
        popTop = targetRect.bottom + margin;
        popLeft = targetRect.left + (targetRect.width - popW) / 2;
      } else if (side === 'top') {
        popTop = targetRect.top - popH - margin;
        popLeft = targetRect.left + (targetRect.width - popW) / 2;
      } else if (side === 'right') {
        popLeft = targetRect.right + margin;
        popTop = targetRect.top + (targetRect.height - popH) / 2;
      } else if (side === 'left') {
        popLeft = targetRect.left - popW - margin;
        popTop = targetRect.top + (targetRect.height - popH) / 2;
      }

      // Viewport safety clamp
      popLeft = clamp(popLeft, 12, winW - popW - 12);
      popTop = clamp(popTop, 12, winH - popH - 12);

      popoverEl.style.top = popTop + 'px';
      popoverEl.style.left = popLeft + 'px';
      popoverEl.setAttribute('data-side', side);

      // Position Arrow
      if (arrowEl) {
        if (side === 'bottom') {
          var arrowX = clamp(targetRect.left + targetRect.width / 2 - popLeft, 16, popW - 24);
          arrowEl.style.top = '-6px';
          arrowEl.style.left = arrowX + 'px';
          arrowEl.style.bottom = '';
          arrowEl.style.right = '';
        } else if (side === 'top') {
          var arrowXTop = clamp(targetRect.left + targetRect.width / 2 - popLeft, 16, popW - 24);
          arrowEl.style.bottom = '-6px';
          arrowEl.style.left = arrowXTop + 'px';
          arrowEl.style.top = '';
          arrowEl.style.right = '';
        } else if (side === 'right') {
          var arrowY = clamp(targetRect.top + targetRect.height / 2 - popTop, 16, popH - 24);
          arrowEl.style.left = '-6px';
          arrowEl.style.top = arrowY + 'px';
          arrowEl.style.right = '';
          arrowEl.style.bottom = '';
        } else if (side === 'left') {
          var arrowYLeft = clamp(targetRect.top + targetRect.height / 2 - popTop, 16, popH - 24);
          arrowEl.style.right = '-6px';
          arrowEl.style.top = arrowYLeft + 'px';
          arrowEl.style.left = '';
          arrowEl.style.bottom = '';
        }
      }

      popoverEl.style.visibility = 'visible';
    }

    function renderPopoverContent(step, index) {
      if (!popoverEl) return;
      var pop = step.popover || {};
      var total = config.steps.length;
      var current = index + 1;

      var titleEl = popoverEl.querySelector('.driver-popover-title');
      var descEl = popoverEl.querySelector('.driver-popover-description');
      var progEl = popoverEl.querySelector('.driver-popover-progress-text');
      var prevBtn = popoverEl.querySelector('.driver-popover-prev-btn');
      var nextBtn = popoverEl.querySelector('.driver-popover-next-btn');
      var closeBtn = popoverEl.querySelector('.driver-popover-close-btn');

      titleEl.textContent = pop.title || '';
      descEl.textContent = pop.description || '';

      // Progress text
      if (config.showProgress) {
        var pText = (config.progressText || '{{current}} / {{total}}')
          .replace('{{current}}', current)
          .replace('{{total}}', total);
        progEl.textContent = pText;
        progEl.style.display = 'inline-block';
      } else {
        progEl.style.display = 'none';
      }

      // Close button
      if (config.allowClose && (!pop.showButtons || pop.showButtons.indexOf('close') !== -1)) {
        closeBtn.style.display = 'inline-flex';
      } else {
        closeBtn.style.display = 'none';
      }

      // Previous button
      if (index > 0 && (!pop.showButtons || pop.showButtons.indexOf('previous') !== -1)) {
        prevBtn.textContent = pop.prevBtnText || config.prevBtnText;
        prevBtn.style.display = 'inline-flex';
      } else {
        prevBtn.style.display = 'none';
      }

      // Next / Finish button
      var isLast = current === total;
      if (!pop.showButtons || pop.showButtons.indexOf('next') !== -1) {
        nextBtn.textContent = isLast
          ? (pop.doneBtnText || config.doneBtnText)
          : (pop.nextBtnText || config.nextBtnText);
        nextBtn.style.display = 'inline-flex';
      } else {
        nextBtn.style.display = 'none';
      }

      if (typeof config.onPopoverRender === 'function') {
        config.onPopoverRender(popoverEl, {
          config: config,
          state: { activeIndex: index },
        });
      }
    }

    function scrollToElement(el) {
      if (!el || !el.getBoundingClientRect) return;
      var rect = el.getBoundingClientRect();
      var isInView = (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= window.innerHeight &&
        rect.right <= window.innerWidth
      );
      if (!isInView) {
        try {
          el.scrollIntoView({
            behavior: (!prefersReducedMotion() && config.animate) ? 'smooth' : 'auto',
            block: 'center',
            inline: 'nearest',
          });
        } catch (e) {
          el.scrollIntoView(false);
        }
      }
    }

    function trapFocus(e) {
      if (!popoverEl || e.key !== 'Tab') return;
      var focusable = popoverEl.querySelectorAll(
        'button:not([style*="display: none"]):not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      var first = focusable[0];
      var last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        last.focus();
        e.preventDefault();
      } else if (!e.shiftKey && document.activeElement === last) {
        first.focus();
        e.preventDefault();
      }
    }

    function onKeyDown(e) {
      if (!isActivated) return;
      if (e.key === 'Escape' && config.allowClose) {
        e.preventDefault();
        destroy();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (hasNextStep()) {
          moveNext();
        } else if (isLastStep()) {
          destroy();
        }
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (hasPreviousStep()) {
          movePrevious();
        }
      } else if (e.key === 'Tab') {
        trapFocus(e);
      }
    }

    function onWindowChange() {
      if (!isActivated) return;
      if (resizeRafId) cancelAnimationFrame(resizeRafId);
      resizeRafId = requestAnimationFrame(function () {
        var step = config.steps[activeIndex];
        if (step) {
          var el = getElement(step.element);
          positionElements(el, step.popover);
        }
      });
    }

    function highlight(stepIndex) {
      if (stepIndex < 0 || stepIndex >= config.steps.length) {
        destroy();
        return;
      }

      activeIndex = stepIndex;
      var step = config.steps[stepIndex];
      var targetEl = getElement(step.element);
      activeElement = targetEl;

      if (typeof config.onHighlightStarted === 'function') {
        config.onHighlightStarted(targetEl, step, {
          config: config,
          state: { activeIndex: activeIndex },
        });
      }

      buildSvgOverlay();
      buildStage();
      buildPopover();

      renderPopoverContent(step, stepIndex);

      if (targetEl) {
        scrollToElement(targetEl);
      }

      // Small delay allows smooth scroll to complete before positioning
      setTimeout(function () {
        positionElements(targetEl, step.popover);
        var nextBtn = popoverEl.querySelector('.driver-popover-next-btn');
        if (nextBtn && nextBtn.style.display !== 'none') {
          nextBtn.focus();
        }

        if (typeof config.onHighlighted === 'function') {
          config.onHighlighted(targetEl, step, {
            config: config,
            state: { activeIndex: activeIndex },
          });
        }
      }, prefersReducedMotion() ? 20 : 120);
    }

    function drive(stepIndex) {
      if (!config.steps || config.steps.length === 0) return;

      lastFocusedElement = document.activeElement;
      isActivated = true;

      window.addEventListener('keydown', onKeyDown, true);
      window.addEventListener('resize', onWindowChange);
      window.addEventListener('scroll', onWindowChange, true);

      highlight(typeof stepIndex === 'number' ? stepIndex : 0);
    }

    function moveNext() {
      if (hasNextStep()) {
        highlight(activeIndex + 1);
      } else {
        destroy();
      }
    }

    function movePrevious() {
      if (hasPreviousStep()) {
        highlight(activeIndex - 1);
      }
    }

    function moveTo(index) {
      highlight(index);
    }

    function hasNextStep() {
      return activeIndex < config.steps.length - 1;
    }

    function hasPreviousStep() {
      return activeIndex > 0;
    }

    function isFirstStep() {
      return activeIndex === 0;
    }

    function isLastStep() {
      return activeIndex === config.steps.length - 1;
    }

    function getActiveIndex() {
      return activeIndex;
    }

    function getActiveStep() {
      return config.steps[activeIndex] || null;
    }

    function getActiveElement() {
      return activeElement;
    }

    function destroy() {
      if (!isActivated) return;
      isActivated = false;
      activeIndex = -1;
      activeElement = null;

      window.removeEventListener('keydown', onKeyDown, true);
      window.removeEventListener('resize', onWindowChange);
      window.removeEventListener('scroll', onWindowChange, true);

      if (resizeRafId) {
        cancelAnimationFrame(resizeRafId);
        resizeRafId = null;
      }

      if (overlaySvg && overlaySvg.parentNode) {
        overlaySvg.parentNode.removeChild(overlaySvg);
      }
      overlaySvg = null;
      overlayPath = null;

      if (stageEl && stageEl.parentNode) {
        stageEl.parentNode.removeChild(stageEl);
      }
      stageEl = null;

      if (popoverEl && popoverEl.parentNode) {
        popoverEl.parentNode.removeChild(popoverEl);
      }
      popoverEl = null;

      if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        try {
          lastFocusedElement.focus();
        } catch (e) {}
      }

      if (typeof config.onDestroyed === 'function') {
        config.onDestroyed();
      }
    }

    return {
      drive: drive,
      moveNext: moveNext,
      movePrevious: movePrevious,
      moveTo: moveTo,
      hasNextStep: hasNextStep,
      hasPreviousStep: hasPreviousStep,
      isFirstStep: isFirstStep,
      isLastStep: isLastStep,
      getActiveIndex: getActiveIndex,
      getActiveStep: getActiveStep,
      getActiveElement: getActiveElement,
      destroy: destroy,
      setConfig: function (newConfig) {
        config = Object.assign({}, config, newConfig);
      },
      getConfig: function () {
        return config;
      },
      refresh: onWindowChange,
    };
  }

  return {
    driver: createDriver,
  };
});
