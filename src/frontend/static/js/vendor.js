/*
 * Compiled JS — DO NOT EDIT
 * Sources: vendor/htmx.js, vendor/htmx-ws.js, vendor/sortable.js, vendor/nprogress.js, vendor/popper.js, vendor/tippy.js, vendor/alpine-persist.js, vendor/alpine-collapse.js, vendor/alpine.js
 * Minified: False
 */


var htmx = (function() {
  'use strict'


  const htmx = {



    onLoad: null,

    process: null,

    on: null,

    off: null,

    trigger: null,

    ajax: null,


    find: null,

    findAll: null,

    closest: null,

    values: function(elt, type) {
      const inputValues = getInputValues(elt, type || 'post')
      return inputValues.values
    },


    remove: null,

    addClass: null,

    removeClass: null,

    toggleClass: null,

    takeClass: null,

    swap: null,


    defineExtension: null,

    removeExtension: null,


    logAll: null,

    logNone: null,


    logger: null,

    config: {

      historyEnabled: true,

      historyCacheSize: 10,

      refreshOnHistoryMiss: false,

      defaultSwapStyle: 'innerHTML',

      defaultSwapDelay: 0,

      defaultSettleDelay: 20,

      includeIndicatorStyles: true,

      indicatorClass: 'htmx-indicator',

      requestClass: 'htmx-request',

      addedClass: 'htmx-added',

      settlingClass: 'htmx-settling',

      swappingClass: 'htmx-swapping',

      allowEval: true,

      allowScriptTags: true,

      inlineScriptNonce: '',

      inlineStyleNonce: '',

      attributesToSettle: ['class', 'style', 'width', 'height'],

      withCredentials: false,

      timeout: 0,

      wsReconnectDelay: 'full-jitter',

      wsBinaryType: 'blob',

      disableSelector: '[hx-disable], [data-hx-disable]',

      scrollBehavior: 'instant',

      defaultFocusScroll: false,

      getCacheBusterParam: false,

      globalViewTransitions: false,

      methodsThatUseUrlParams: ['get', 'delete'],

      selfRequestsOnly: true,

      ignoreTitle: false,

      scrollIntoViewOnBoost: true,

      triggerSpecsCache: null,

      disableInheritance: false,

      responseHandling: [
        { code: '204', swap: false },
        { code: '[23]..', swap: true },
        { code: '[45]..', swap: false, error: true }
      ],

      allowNestedOobSwaps: true
    },

    parseInterval: null,

    _: null,
    version: '2.0.4'
  }

  htmx.onLoad = onLoadHelper
  htmx.process = processNode
  htmx.on = addEventListenerImpl
  htmx.off = removeEventListenerImpl
  htmx.trigger = triggerEvent
  htmx.ajax = ajaxHelper
  htmx.find = find
  htmx.findAll = findAll
  htmx.closest = closest
  htmx.remove = removeElement
  htmx.addClass = addClassToElement
  htmx.removeClass = removeClassFromElement
  htmx.toggleClass = toggleClassOnElement
  htmx.takeClass = takeClassForElement
  htmx.swap = swap
  htmx.defineExtension = defineExtension
  htmx.removeExtension = removeExtension
  htmx.logAll = logAll
  htmx.logNone = logNone
  htmx.parseInterval = parseInterval
  htmx._ = internalEval

  const internalAPI = {
    addTriggerHandler,
    bodyContains,
    canAccessLocalStorage,
    findThisElement,
    filterValues,
    swap,
    hasAttribute,
    getAttributeValue,
    getClosestAttributeValue,
    getClosestMatch,
    getExpressionVars,
    getHeaders,
    getInputValues,
    getInternalData,
    getSwapSpecification,
    getTriggerSpecs,
    getTarget,
    makeFragment,
    mergeObjects,
    makeSettleInfo,
    oobSwap,
    querySelectorExt,
    settleImmediately,
    shouldCancel,
    triggerEvent,
    triggerErrorEvent,
    withExtensions
  }

  const VERBS = ['get', 'post', 'put', 'delete', 'patch']
  const VERB_SELECTOR = VERBS.map(function(verb) {
    return '[hx-' + verb + '], [data-hx-' + verb + ']'
  }).join(', ')






  function parseInterval(str) {
    if (str == undefined) {
      return undefined
    }

    let interval = NaN
    if (str.slice(-2) == 'ms') {
      interval = parseFloat(str.slice(0, -2))
    } else if (str.slice(-1) == 's') {
      interval = parseFloat(str.slice(0, -1)) * 1000
    } else if (str.slice(-1) == 'm') {
      interval = parseFloat(str.slice(0, -1)) * 1000 * 60
    } else {
      interval = parseFloat(str)
    }
    return isNaN(interval) ? undefined : interval
  }


  function getRawAttribute(elt, name) {
    return elt instanceof Element && elt.getAttribute(name)
  }



  function hasAttribute(elt, qualifiedName) {
    return !!elt.hasAttribute && (elt.hasAttribute(qualifiedName) ||
      elt.hasAttribute('data-' + qualifiedName))
  }


  function getAttributeValue(elt, qualifiedName) {
    return getRawAttribute(elt, qualifiedName) || getRawAttribute(elt, 'data-' + qualifiedName)
  }


  function parentElt(elt) {
    const parent = elt.parentElement
    if (!parent && elt.parentNode instanceof ShadowRoot) return elt.parentNode
    return parent
  }


  function getDocument() {
    return document
  }


  function getRootNode(elt, global) {
    return elt.getRootNode ? elt.getRootNode({ composed: global }) : getDocument()
  }


  function getClosestMatch(elt, condition) {
    while (elt && !condition(elt)) {
      elt = parentElt(elt)
    }

    return elt || null
  }


  function getAttributeValueWithDisinheritance(initialElement, ancestor, attributeName) {
    const attributeValue = getAttributeValue(ancestor, attributeName)
    const disinherit = getAttributeValue(ancestor, 'hx-disinherit')
    var inherit = getAttributeValue(ancestor, 'hx-inherit')
    if (initialElement !== ancestor) {
      if (htmx.config.disableInheritance) {
        if (inherit && (inherit === '*' || inherit.split(' ').indexOf(attributeName) >= 0)) {
          return attributeValue
        } else {
          return null
        }
      }
      if (disinherit && (disinherit === '*' || disinherit.split(' ').indexOf(attributeName) >= 0)) {
        return 'unset'
      }
    }
    return attributeValue
  }


  function getClosestAttributeValue(elt, attributeName) {
    let closestAttr = null
    getClosestMatch(elt, function(e) {
      return !!(closestAttr = getAttributeValueWithDisinheritance(elt, asElement(e), attributeName))
    })
    if (closestAttr !== 'unset') {
      return closestAttr
    }
  }


  function matches(elt, selector) {


    const matchesFunction = elt instanceof Element && (elt.matches || elt.matchesSelector || elt.msMatchesSelector || elt.mozMatchesSelector || elt.webkitMatchesSelector || elt.oMatchesSelector)
    return !!matchesFunction && matchesFunction.call(elt, selector)
  }


  function getStartTag(str) {
    const tagMatcher = /<([a-z][^\/\0>\x20\t\r\n\f]*)/i
    const match = tagMatcher.exec(str)
    if (match) {
      return match[1].toLowerCase()
    } else {
      return ''
    }
  }


  function parseHTML(resp) {
    const parser = new DOMParser()
    return parser.parseFromString(resp, 'text/html')
  }


  function takeChildrenFor(fragment, elt) {
    while (elt.childNodes.length > 0) {
      fragment.append(elt.childNodes[0])
    }
  }


  function duplicateScript(script) {
    const newScript = getDocument().createElement('script')
    forEach(script.attributes, function(attr) {
      newScript.setAttribute(attr.name, attr.value)
    })
    newScript.textContent = script.textContent
    newScript.async = false
    if (htmx.config.inlineScriptNonce) {
      newScript.nonce = htmx.config.inlineScriptNonce
    }
    return newScript
  }


  function isJavaScriptScriptNode(script) {
    return script.matches('script') && (script.type === 'text/javascript' || script.type === 'module' || script.type === '')
  }


  function normalizeScriptTags(fragment) {
    Array.from(fragment.querySelectorAll('script')).forEach( (script) => {
      if (isJavaScriptScriptNode(script)) {
        const newScript = duplicateScript(script)
        const parent = script.parentNode
        try {
          parent.insertBefore(newScript, script)
        } catch (e) {
          logError(e)
        } finally {
          script.remove()
        }
      }
    })
  }




  function makeFragment(response) {

    const responseWithNoHead = response.replace(/<head(\s[^>]*)?>[\s\S]*?<\/head>/i, '')
    const startTag = getStartTag(responseWithNoHead)

    let fragment
    if (startTag === 'html') {

      fragment =  (new DocumentFragment())
      const doc = parseHTML(response)
      takeChildrenFor(fragment, doc.body)
      fragment.title = doc.title
    } else if (startTag === 'body') {

      fragment =  (new DocumentFragment())
      const doc = parseHTML(responseWithNoHead)
      takeChildrenFor(fragment, doc.body)
      fragment.title = doc.title
    } else {

      const doc = parseHTML('<body><template class="internal-htmx-wrapper">' + responseWithNoHead + '</template></body>')
      fragment =  (doc.querySelector('template').content)

      fragment.title = doc.title


      var titleElement = fragment.querySelector('title')
      if (titleElement && titleElement.parentNode === fragment) {
        titleElement.remove()
        fragment.title = titleElement.innerText
      }
    }
    if (fragment) {
      if (htmx.config.allowScriptTags) {
        normalizeScriptTags(fragment)
      } else {

        fragment.querySelectorAll('script').forEach((script) => script.remove())
      }
    }
    return fragment
  }


  function maybeCall(func) {
    if (func) {
      func()
    }
  }


  function isType(o, type) {
    return Object.prototype.toString.call(o) === '[object ' + type + ']'
  }


  function isFunction(o) {
    return typeof o === 'function'
  }


  function isRawObject(o) {
    return isType(o, 'Object')
  }








  function getInternalData(elt) {
    const dataProp = 'htmx-internal-data'
    let data = elt[dataProp]
    if (!data) {
      data = elt[dataProp] = {}
    }
    return data
  }


  function toArray(arr) {
    const returnArr = []
    if (arr) {
      for (let i = 0; i < arr.length; i++) {
        returnArr.push(arr[i])
      }
    }
    return returnArr
  }


  function forEach(arr, func) {
    if (arr) {
      for (let i = 0; i < arr.length; i++) {
        func(arr[i])
      }
    }
  }


  function isScrolledIntoView(el) {
    const rect = el.getBoundingClientRect()
    const elemTop = rect.top
    const elemBottom = rect.bottom
    return elemTop < window.innerHeight && elemBottom >= 0
  }


  function bodyContains(elt) {
    return elt.getRootNode({ composed: true }) === document
  }


  function splitOnWhitespace(trigger) {
    return trigger.trim().split(/\s+/)
  }


  function mergeObjects(obj1, obj2) {
    for (const key in obj2) {
      if (obj2.hasOwnProperty(key)) {

        obj1[key] = obj2[key]
      }
    }

    return obj1
  }


  function parseJSON(jString) {
    try {
      return JSON.parse(jString)
    } catch (error) {
      logError(error)
      return null
    }
  }


  function canAccessLocalStorage() {
    const test = 'htmx:localStorageTest'
    try {
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch (e) {
      return false
    }
  }


  function normalizePath(path) {
    try {
      const url = new URL(path)
      if (url) {
        path = url.pathname + url.search
      }

      if (!(/^\/$/.test(path))) {
        path = path.replace(/\/+$/, '')
      }
      return path
    } catch (e) {

      return path
    }
  }






  function internalEval(str) {
    return maybeEval(getDocument().body, function() {
      return eval(str)
    })
  }


  function onLoadHelper(callback) {
    const value = htmx.on('htmx:load',  function(evt) {
      callback(evt.detail.elt)
    })
    return value
  }


  function logAll() {
    htmx.logger = function(elt, event, data) {
      if (console) {
        console.log(event, elt, data)
      }
    }
  }

  function logNone() {
    htmx.logger = null
  }


  function find(eltOrSelector, selector) {
    if (typeof eltOrSelector !== 'string') {
      return eltOrSelector.querySelector(selector)
    } else {
      return find(getDocument(), eltOrSelector)
    }
  }


  function findAll(eltOrSelector, selector) {
    if (typeof eltOrSelector !== 'string') {
      return eltOrSelector.querySelectorAll(selector)
    } else {
      return findAll(getDocument(), eltOrSelector)
    }
  }


  function getWindow() {
    return window
  }


  function removeElement(elt, delay) {
    elt = resolveTarget(elt)
    if (delay) {
      getWindow().setTimeout(function() {
        removeElement(elt)
        elt = null
      }, delay)
    } else {
      parentElt(elt).removeChild(elt)
    }
  }


  function asElement(elt) {
    return elt instanceof Element ? elt : null
  }


  function asHtmlElement(elt) {
    return elt instanceof HTMLElement ? elt : null
  }


  function asString(value) {
    return typeof value === 'string' ? value : null
  }


  function asParentNode(elt) {
    return elt instanceof Element || elt instanceof Document || elt instanceof DocumentFragment ? elt : null
  }


  function addClassToElement(elt, clazz, delay) {
    elt = asElement(resolveTarget(elt))
    if (!elt) {
      return
    }
    if (delay) {
      getWindow().setTimeout(function() {
        addClassToElement(elt, clazz)
        elt = null
      }, delay)
    } else {
      elt.classList && elt.classList.add(clazz)
    }
  }


  function removeClassFromElement(node, clazz, delay) {
    let elt = asElement(resolveTarget(node))
    if (!elt) {
      return
    }
    if (delay) {
      getWindow().setTimeout(function() {
        removeClassFromElement(elt, clazz)
        elt = null
      }, delay)
    } else {
      if (elt.classList) {
        elt.classList.remove(clazz)

        if (elt.classList.length === 0) {
          elt.removeAttribute('class')
        }
      }
    }
  }


  function toggleClassOnElement(elt, clazz) {
    elt = resolveTarget(elt)
    elt.classList.toggle(clazz)
  }


  function takeClassForElement(elt, clazz) {
    elt = resolveTarget(elt)
    forEach(elt.parentElement.children, function(child) {
      removeClassFromElement(child, clazz)
    })
    addClassToElement(asElement(elt), clazz)
  }


  function closest(elt, selector) {
    elt = asElement(resolveTarget(elt))
    if (elt && elt.closest) {
      return elt.closest(selector)
    } else {

      do {
        if (elt == null || matches(elt, selector)) {
          return elt
        }
      }
      while (elt = elt && asElement(parentElt(elt)))
      return null
    }
  }


  function startsWith(str, prefix) {
    return str.substring(0, prefix.length) === prefix
  }


  function endsWith(str, suffix) {
    return str.substring(str.length - suffix.length) === suffix
  }


  function normalizeSelector(selector) {
    const trimmedSelector = selector.trim()
    if (startsWith(trimmedSelector, '<') && endsWith(trimmedSelector, '/>')) {
      return trimmedSelector.substring(1, trimmedSelector.length - 2)
    } else {
      return trimmedSelector
    }
  }


  function querySelectorAllExt(elt, selector, global) {
    if (selector.indexOf('global ') === 0) {
      return querySelectorAllExt(elt, selector.slice(7), true)
    }

    elt = resolveTarget(elt)

    const parts = []
    {
      let chevronsCount = 0
      let offset = 0
      for (let i = 0; i < selector.length; i++) {
        const char = selector[i]
        if (char === ',' && chevronsCount === 0) {
          parts.push(selector.substring(offset, i))
          offset = i + 1
          continue
        }
        if (char === '<') {
          chevronsCount++
        } else if (char === '/' && i < selector.length - 1 && selector[i + 1] === '>') {
          chevronsCount--
        }
      }
      if (offset < selector.length) {
        parts.push(selector.substring(offset))
      }
    }

    const result = []
    const unprocessedParts = []
    while (parts.length > 0) {
      const selector = normalizeSelector(parts.shift())
      let item
      if (selector.indexOf('closest ') === 0) {
        item = closest(asElement(elt), normalizeSelector(selector.substr(8)))
      } else if (selector.indexOf('find ') === 0) {
        item = find(asParentNode(elt), normalizeSelector(selector.substr(5)))
      } else if (selector === 'next' || selector === 'nextElementSibling') {
        item = asElement(elt).nextElementSibling
      } else if (selector.indexOf('next ') === 0) {
        item = scanForwardQuery(elt, normalizeSelector(selector.substr(5)), !!global)
      } else if (selector === 'previous' || selector === 'previousElementSibling') {
        item = asElement(elt).previousElementSibling
      } else if (selector.indexOf('previous ') === 0) {
        item = scanBackwardsQuery(elt, normalizeSelector(selector.substr(9)), !!global)
      } else if (selector === 'document') {
        item = document
      } else if (selector === 'window') {
        item = window
      } else if (selector === 'body') {
        item = document.body
      } else if (selector === 'root') {
        item = getRootNode(elt, !!global)
      } else if (selector === 'host') {
        item = ((elt.getRootNode())).host
      } else {
        unprocessedParts.push(selector)
      }

      if (item) {
        result.push(item)
      }
    }

    if (unprocessedParts.length > 0) {
      const standardSelector = unprocessedParts.join(',')
      const rootNode = asParentNode(getRootNode(elt, !!global))
      result.push(...toArray(rootNode.querySelectorAll(standardSelector)))
    }

    return result
  }


  var scanForwardQuery = function(start, match, global) {
    const results = asParentNode(getRootNode(start, global)).querySelectorAll(match)
    for (let i = 0; i < results.length; i++) {
      const elt = results[i]
      if (elt.compareDocumentPosition(start) === Node.DOCUMENT_POSITION_PRECEDING) {
        return elt
      }
    }
  }


  var scanBackwardsQuery = function(start, match, global) {
    const results = asParentNode(getRootNode(start, global)).querySelectorAll(match)
    for (let i = results.length - 1; i >= 0; i--) {
      const elt = results[i]
      if (elt.compareDocumentPosition(start) === Node.DOCUMENT_POSITION_FOLLOWING) {
        return elt
      }
    }
  }


  function querySelectorExt(eltOrSelector, selector) {
    if (typeof eltOrSelector !== 'string') {
      return querySelectorAllExt(eltOrSelector, selector)[0]
    } else {
      return querySelectorAllExt(getDocument().body, eltOrSelector)[0]
    }
  }


  function resolveTarget(eltOrSelector, context) {
    if (typeof eltOrSelector === 'string') {
      return find(asParentNode(context) || document, eltOrSelector)
    } else {
      return eltOrSelector
    }
  }






  function processEventArgs(arg1, arg2, arg3, arg4) {
    if (isFunction(arg2)) {
      return {
        target: getDocument().body,
        event: asString(arg1),
        listener: arg2,
        options: arg3
      }
    } else {
      return {
        target: resolveTarget(arg1),
        event: asString(arg2),
        listener: arg3,
        options: arg4
      }
    }
  }


  function addEventListenerImpl(arg1, arg2, arg3, arg4) {
    ready(function() {
      const eventArgs = processEventArgs(arg1, arg2, arg3, arg4)
      eventArgs.target.addEventListener(eventArgs.event, eventArgs.listener, eventArgs.options)
    })
    const b = isFunction(arg2)
    return b ? arg2 : arg3
  }


  function removeEventListenerImpl(arg1, arg2, arg3) {
    ready(function() {
      const eventArgs = processEventArgs(arg1, arg2, arg3)
      eventArgs.target.removeEventListener(eventArgs.event, eventArgs.listener)
    })
    return isFunction(arg2) ? arg2 : arg3
  }





  const DUMMY_ELT = getDocument().createElement('output')

  function findAttributeTargets(elt, attrName) {
    const attrTarget = getClosestAttributeValue(elt, attrName)
    if (attrTarget) {
      if (attrTarget === 'this') {
        return [findThisElement(elt, attrName)]
      } else {
        const result = querySelectorAllExt(elt, attrTarget)
        if (result.length === 0) {
          logError('The selector "' + attrTarget + '" on ' + attrName + ' returned no matches!')
          return [DUMMY_ELT]
        } else {
          return result
        }
      }
    }
  }


  function findThisElement(elt, attribute) {
    return asElement(getClosestMatch(elt, function(elt) {
      return getAttributeValue(asElement(elt), attribute) != null
    }))
  }


  function getTarget(elt) {
    const targetStr = getClosestAttributeValue(elt, 'hx-target')
    if (targetStr) {
      if (targetStr === 'this') {
        return findThisElement(elt, 'hx-target')
      } else {
        return querySelectorExt(elt, targetStr)
      }
    } else {
      const data = getInternalData(elt)
      if (data.boosted) {
        return getDocument().body
      } else {
        return elt
      }
    }
  }


  function shouldSettleAttribute(name) {
    const attributesToSettle = htmx.config.attributesToSettle
    for (let i = 0; i < attributesToSettle.length; i++) {
      if (name === attributesToSettle[i]) {
        return true
      }
    }
    return false
  }


  function cloneAttributes(mergeTo, mergeFrom) {
    forEach(mergeTo.attributes, function(attr) {
      if (!mergeFrom.hasAttribute(attr.name) && shouldSettleAttribute(attr.name)) {
        mergeTo.removeAttribute(attr.name)
      }
    })
    forEach(mergeFrom.attributes, function(attr) {
      if (shouldSettleAttribute(attr.name)) {
        mergeTo.setAttribute(attr.name, attr.value)
      }
    })
  }


  function isInlineSwap(swapStyle, target) {
    const extensions = getExtensions(target)
    for (let i = 0; i < extensions.length; i++) {
      const extension = extensions[i]
      try {
        if (extension.isInlineSwap(swapStyle)) {
          return true
        }
      } catch (e) {
        logError(e)
      }
    }
    return swapStyle === 'outerHTML'
  }


  function oobSwap(oobValue, oobElement, settleInfo, rootNode) {
    rootNode = rootNode || getDocument()
    let selector = '#' + getRawAttribute(oobElement, 'id')

    let swapStyle = 'outerHTML'
    if (oobValue === 'true') {

    } else if (oobValue.indexOf(':') > 0) {
      swapStyle = oobValue.substring(0, oobValue.indexOf(':'))
      selector = oobValue.substring(oobValue.indexOf(':') + 1)
    } else {
      swapStyle = oobValue
    }
    oobElement.removeAttribute('hx-swap-oob')
    oobElement.removeAttribute('data-hx-swap-oob')

    const targets = querySelectorAllExt(rootNode, selector, false)
    if (targets) {
      forEach(
        targets,
        function(target) {
          let fragment
          const oobElementClone = oobElement.cloneNode(true)
          fragment = getDocument().createDocumentFragment()
          fragment.appendChild(oobElementClone)
          if (!isInlineSwap(swapStyle, target)) {
            fragment = asParentNode(oobElementClone)
          }

          const beforeSwapDetails = { shouldSwap: true, target, fragment }
          if (!triggerEvent(target, 'htmx:oobBeforeSwap', beforeSwapDetails)) return

          target = beforeSwapDetails.target
          if (beforeSwapDetails.shouldSwap) {
            handlePreservedElements(fragment)
            swapWithStyle(swapStyle, target, target, fragment, settleInfo)
            restorePreservedElements()
          }
          forEach(settleInfo.elts, function(elt) {
            triggerEvent(elt, 'htmx:oobAfterSwap', beforeSwapDetails)
          })
        }
      )
      oobElement.parentNode.removeChild(oobElement)
    } else {
      oobElement.parentNode.removeChild(oobElement)
      triggerErrorEvent(getDocument().body, 'htmx:oobErrorNoTarget', { content: oobElement })
    }
    return oobValue
  }

  function restorePreservedElements() {
    const pantry = find('#--htmx-preserve-pantry--')
    if (pantry) {
      for (const preservedElt of [...pantry.children]) {
        const existingElement = find('#' + preservedElt.id)

        existingElement.parentNode.moveBefore(preservedElt, existingElement)
        existingElement.remove()
      }
      pantry.remove()
    }
  }


  function handlePreservedElements(fragment) {
    forEach(findAll(fragment, '[hx-preserve], [data-hx-preserve]'), function(preservedElt) {
      const id = getAttributeValue(preservedElt, 'id')
      const existingElement = getDocument().getElementById(id)
      if (existingElement != null) {
        if (preservedElt.moveBefore) {

          let pantry = find('#--htmx-preserve-pantry--')
          if (pantry == null) {
            getDocument().body.insertAdjacentHTML('afterend', "<div id='--htmx-preserve-pantry--'></div>")
            pantry = find('#--htmx-preserve-pantry--')
          }

          pantry.moveBefore(existingElement, null)
        } else {
          preservedElt.parentNode.replaceChild(existingElement, preservedElt)
        }
      }
    })
  }


  function handleAttributes(parentNode, fragment, settleInfo) {
    forEach(fragment.querySelectorAll('[id]'), function(newNode) {
      const id = getRawAttribute(newNode, 'id')
      if (id && id.length > 0) {
        const normalizedId = id.replace("'", "\\'")
        const normalizedTag = newNode.tagName.replace(':', '\\:')
        const parentElt = asParentNode(parentNode)
        const oldNode = parentElt && parentElt.querySelector(normalizedTag + "[id='" + normalizedId + "']")
        if (oldNode && oldNode !== parentElt) {
          const newAttributes = newNode.cloneNode()
          cloneAttributes(newNode, oldNode)
          settleInfo.tasks.push(function() {
            cloneAttributes(newNode, newAttributes)
          })
        }
      }
    })
  }


  function makeAjaxLoadTask(child) {
    return function() {
      removeClassFromElement(child, htmx.config.addedClass)
      processNode(asElement(child))
      processFocus(asParentNode(child))
      triggerEvent(child, 'htmx:load')
    }
  }


  function processFocus(child) {
    const autofocus = '[autofocus]'
    const autoFocusedElt = asHtmlElement(matches(child, autofocus) ? child : child.querySelector(autofocus))
    if (autoFocusedElt != null) {
      autoFocusedElt.focus()
    }
  }


  function insertNodesBefore(parentNode, insertBefore, fragment, settleInfo) {
    handleAttributes(parentNode, fragment, settleInfo)
    while (fragment.childNodes.length > 0) {
      const child = fragment.firstChild
      addClassToElement(asElement(child), htmx.config.addedClass)
      parentNode.insertBefore(child, insertBefore)
      if (child.nodeType !== Node.TEXT_NODE && child.nodeType !== Node.COMMENT_NODE) {
        settleInfo.tasks.push(makeAjaxLoadTask(child))
      }
    }
  }


  function stringHash(string, hash) {
    let char = 0
    while (char < string.length) {
      hash = (hash << 5) - hash + string.charCodeAt(char++) | 0
    }
    return hash
  }


  function attributeHash(elt) {
    let hash = 0

    if (elt.attributes) {
      for (let i = 0; i < elt.attributes.length; i++) {
        const attribute = elt.attributes[i]
        if (attribute.value) {
          hash = stringHash(attribute.name, hash)
          hash = stringHash(attribute.value, hash)
        }
      }
    }
    return hash
  }


  function deInitOnHandlers(elt) {
    const internalData = getInternalData(elt)
    if (internalData.onHandlers) {
      for (let i = 0; i < internalData.onHandlers.length; i++) {
        const handlerInfo = internalData.onHandlers[i]
        removeEventListenerImpl(elt, handlerInfo.event, handlerInfo.listener)
      }
      delete internalData.onHandlers
    }
  }


  function deInitNode(element) {
    const internalData = getInternalData(element)
    if (internalData.timeout) {
      clearTimeout(internalData.timeout)
    }
    if (internalData.listenerInfos) {
      forEach(internalData.listenerInfos, function(info) {
        if (info.on) {
          removeEventListenerImpl(info.on, info.trigger, info.listener)
        }
      })
    }
    deInitOnHandlers(element)
    forEach(Object.keys(internalData), function(key) { if (key !== 'firstInitCompleted') delete internalData[key] })
  }


  function cleanUpElement(element) {
    triggerEvent(element, 'htmx:beforeCleanupElement')
    deInitNode(element)


    if (element.children) {

      forEach(element.children, function(child) { cleanUpElement(child) })
    }
  }


  function swapOuterHTML(target, fragment, settleInfo) {
    if (target instanceof Element && target.tagName === 'BODY') {
      return swapInnerHTML(target, fragment, settleInfo)
    }

    let newElt
    const eltBeforeNewContent = target.previousSibling
    const parentNode = parentElt(target)
    if (!parentNode) {
      return
    }
    insertNodesBefore(parentNode, target, fragment, settleInfo)
    if (eltBeforeNewContent == null) {
      newElt = parentNode.firstChild
    } else {
      newElt = eltBeforeNewContent.nextSibling
    }
    settleInfo.elts = settleInfo.elts.filter(function(e) { return e !== target })


    while (newElt && newElt !== target) {
      if (newElt instanceof Element) {
        settleInfo.elts.push(newElt)
      }
      newElt = newElt.nextSibling
    }
    cleanUpElement(target)
    if (target instanceof Element) {
      target.remove()
    } else {
      target.parentNode.removeChild(target)
    }
  }


  function swapAfterBegin(target, fragment, settleInfo) {
    return insertNodesBefore(target, target.firstChild, fragment, settleInfo)
  }


  function swapBeforeBegin(target, fragment, settleInfo) {
    return insertNodesBefore(parentElt(target), target, fragment, settleInfo)
  }


  function swapBeforeEnd(target, fragment, settleInfo) {
    return insertNodesBefore(target, null, fragment, settleInfo)
  }


  function swapAfterEnd(target, fragment, settleInfo) {
    return insertNodesBefore(parentElt(target), target.nextSibling, fragment, settleInfo)
  }


  function swapDelete(target) {
    cleanUpElement(target)
    const parent = parentElt(target)
    if (parent) {
      return parent.removeChild(target)
    }
  }


  function swapInnerHTML(target, fragment, settleInfo) {
    const firstChild = target.firstChild
    insertNodesBefore(target, firstChild, fragment, settleInfo)
    if (firstChild) {
      while (firstChild.nextSibling) {
        cleanUpElement(firstChild.nextSibling)
        target.removeChild(firstChild.nextSibling)
      }
      cleanUpElement(firstChild)
      target.removeChild(firstChild)
    }
  }


  function swapWithStyle(swapStyle, elt, target, fragment, settleInfo) {
    switch (swapStyle) {
      case 'none':
        return
      case 'outerHTML':
        swapOuterHTML(target, fragment, settleInfo)
        return
      case 'afterbegin':
        swapAfterBegin(target, fragment, settleInfo)
        return
      case 'beforebegin':
        swapBeforeBegin(target, fragment, settleInfo)
        return
      case 'beforeend':
        swapBeforeEnd(target, fragment, settleInfo)
        return
      case 'afterend':
        swapAfterEnd(target, fragment, settleInfo)
        return
      case 'delete':
        swapDelete(target)
        return
      default:
        var extensions = getExtensions(elt)
        for (let i = 0; i < extensions.length; i++) {
          const ext = extensions[i]
          try {
            const newElements = ext.handleSwap(swapStyle, target, fragment, settleInfo)
            if (newElements) {
              if (Array.isArray(newElements)) {

                for (let j = 0; j < newElements.length; j++) {
                  const child = newElements[j]
                  if (child.nodeType !== Node.TEXT_NODE && child.nodeType !== Node.COMMENT_NODE) {
                    settleInfo.tasks.push(makeAjaxLoadTask(child))
                  }
                }
              }
              return
            }
          } catch (e) {
            logError(e)
          }
        }
        if (swapStyle === 'innerHTML') {
          swapInnerHTML(target, fragment, settleInfo)
        } else {
          swapWithStyle(htmx.config.defaultSwapStyle, elt, target, fragment, settleInfo)
        }
    }
  }


  function findAndSwapOobElements(fragment, settleInfo, rootNode) {
    var oobElts = findAll(fragment, '[hx-swap-oob], [data-hx-swap-oob]')
    forEach(oobElts, function(oobElement) {
      if (htmx.config.allowNestedOobSwaps || oobElement.parentElement === null) {
        const oobValue = getAttributeValue(oobElement, 'hx-swap-oob')
        if (oobValue != null) {
          oobSwap(oobValue, oobElement, settleInfo, rootNode)
        }
      } else {
        oobElement.removeAttribute('hx-swap-oob')
        oobElement.removeAttribute('data-hx-swap-oob')
      }
    })
    return oobElts.length > 0
  }


  function swap(target, content, swapSpec, swapOptions) {
    if (!swapOptions) {
      swapOptions = {}
    }

    target = resolveTarget(target)
    const rootNode = swapOptions.contextElement ? getRootNode(swapOptions.contextElement, false) : getDocument()


    const activeElt = document.activeElement
    let selectionInfo = {}
    try {
      selectionInfo = {
        elt: activeElt,

        start: activeElt ? activeElt.selectionStart : null,

        end: activeElt ? activeElt.selectionEnd : null
      }
    } catch (e) {

    }
    const settleInfo = makeSettleInfo(target)


    if (swapSpec.swapStyle === 'textContent') {
      target.textContent = content

    } else {
      let fragment = makeFragment(content)

      settleInfo.title = fragment.title


      if (swapOptions.selectOOB) {
        const oobSelectValues = swapOptions.selectOOB.split(',')
        for (let i = 0; i < oobSelectValues.length; i++) {
          const oobSelectValue = oobSelectValues[i].split(':', 2)
          let id = oobSelectValue[0].trim()
          if (id.indexOf('#') === 0) {
            id = id.substring(1)
          }
          const oobValue = oobSelectValue[1] || 'true'
          const oobElement = fragment.querySelector('#' + id)
          if (oobElement) {
            oobSwap(oobValue, oobElement, settleInfo, rootNode)
          }
        }
      }

      findAndSwapOobElements(fragment, settleInfo, rootNode)
      forEach(findAll(fragment, 'template'), function(template) {
        if (template.content && findAndSwapOobElements(template.content, settleInfo, rootNode)) {

          template.remove()
        }
      })


      if (swapOptions.select) {
        const newFragment = getDocument().createDocumentFragment()
        forEach(fragment.querySelectorAll(swapOptions.select), function(node) {
          newFragment.appendChild(node)
        })
        fragment = newFragment
      }
      handlePreservedElements(fragment)
      swapWithStyle(swapSpec.swapStyle, swapOptions.contextElement, target, fragment, settleInfo)
      restorePreservedElements()
    }


    if (selectionInfo.elt &&
      !bodyContains(selectionInfo.elt) &&
      getRawAttribute(selectionInfo.elt, 'id')) {
      const newActiveElt = document.getElementById(getRawAttribute(selectionInfo.elt, 'id'))
      const focusOptions = { preventScroll: swapSpec.focusScroll !== undefined ? !swapSpec.focusScroll : !htmx.config.defaultFocusScroll }
      if (newActiveElt) {

        if (selectionInfo.start && newActiveElt.setSelectionRange) {
          try {

            newActiveElt.setSelectionRange(selectionInfo.start, selectionInfo.end)
          } catch (e) {

          }
        }
        newActiveElt.focus(focusOptions)
      }
    }

    target.classList.remove(htmx.config.swappingClass)
    forEach(settleInfo.elts, function(elt) {
      if (elt.classList) {
        elt.classList.add(htmx.config.settlingClass)
      }
      triggerEvent(elt, 'htmx:afterSwap', swapOptions.eventInfo)
    })
    if (swapOptions.afterSwapCallback) {
      swapOptions.afterSwapCallback()
    }


    if (!swapSpec.ignoreTitle) {
      handleTitle(settleInfo.title)
    }


    const doSettle = function() {
      forEach(settleInfo.tasks, function(task) {
        task.call()
      })
      forEach(settleInfo.elts, function(elt) {
        if (elt.classList) {
          elt.classList.remove(htmx.config.settlingClass)
        }
        triggerEvent(elt, 'htmx:afterSettle', swapOptions.eventInfo)
      })

      if (swapOptions.anchor) {
        const anchorTarget = asElement(resolveTarget('#' + swapOptions.anchor))
        if (anchorTarget) {
          anchorTarget.scrollIntoView({ block: 'start', behavior: 'auto' })
        }
      }

      updateScrollState(settleInfo.elts, swapSpec)
      if (swapOptions.afterSettleCallback) {
        swapOptions.afterSettleCallback()
      }
    }

    if (swapSpec.settleDelay > 0) {
      getWindow().setTimeout(doSettle, swapSpec.settleDelay)
    } else {
      doSettle()
    }
  }


  function handleTriggerHeader(xhr, header, elt) {
    const triggerBody = xhr.getResponseHeader(header)
    if (triggerBody.indexOf('{') === 0) {
      const triggers = parseJSON(triggerBody)
      for (const eventName in triggers) {
        if (triggers.hasOwnProperty(eventName)) {
          let detail = triggers[eventName]
          if (isRawObject(detail)) {

            elt = detail.target !== undefined ? detail.target : elt
          } else {
            detail = { value: detail }
          }
          triggerEvent(elt, eventName, detail)
        }
      }
    } else {
      const eventNames = triggerBody.split(',')
      for (let i = 0; i < eventNames.length; i++) {
        triggerEvent(elt, eventNames[i].trim(), [])
      }
    }
  }

  const WHITESPACE = /\s/
  const WHITESPACE_OR_COMMA = /[\s,]/
  const SYMBOL_START = /[_$a-zA-Z]/
  const SYMBOL_CONT = /[_$a-zA-Z0-9]/
  const STRINGISH_START = ['"', "'", '/']
  const NOT_WHITESPACE = /[^\s]/
  const COMBINED_SELECTOR_START = /[{(]/
  const COMBINED_SELECTOR_END = /[})]/


  function tokenizeString(str) {

    const tokens = []
    let position = 0
    while (position < str.length) {
      if (SYMBOL_START.exec(str.charAt(position))) {
        var startPosition = position
        while (SYMBOL_CONT.exec(str.charAt(position + 1))) {
          position++
        }
        tokens.push(str.substring(startPosition, position + 1))
      } else if (STRINGISH_START.indexOf(str.charAt(position)) !== -1) {
        const startChar = str.charAt(position)
        var startPosition = position
        position++
        while (position < str.length && str.charAt(position) !== startChar) {
          if (str.charAt(position) === '\\') {
            position++
          }
          position++
        }
        tokens.push(str.substring(startPosition, position + 1))
      } else {
        const symbol = str.charAt(position)
        tokens.push(symbol)
      }
      position++
    }
    return tokens
  }


  function isPossibleRelativeReference(token, last, paramName) {
    return SYMBOL_START.exec(token.charAt(0)) &&
      token !== 'true' &&
      token !== 'false' &&
      token !== 'this' &&
      token !== paramName &&
      last !== '.'
  }


  function maybeGenerateConditional(elt, tokens, paramName) {
    if (tokens[0] === '[') {
      tokens.shift()
      let bracketCount = 1
      let conditionalSource = ' return (function(' + paramName + '){ return ('
      let last = null
      while (tokens.length > 0) {
        const token = tokens[0]

        if (token === ']') {
          bracketCount--
          if (bracketCount === 0) {
            if (last === null) {
              conditionalSource = conditionalSource + 'true'
            }
            tokens.shift()
            conditionalSource += ')})'
            try {
              const conditionFunction = maybeEval(elt, function() {
                return Function(conditionalSource)()
              },
              function() { return true })
              conditionFunction.source = conditionalSource
              return conditionFunction
            } catch (e) {
              triggerErrorEvent(getDocument().body, 'htmx:syntax:error', { error: e, source: conditionalSource })
              return null
            }
          }
        } else if (token === '[') {
          bracketCount++
        }
        if (isPossibleRelativeReference(token, last, paramName)) {
          conditionalSource += '((' + paramName + '.' + token + ') ? (' + paramName + '.' + token + ') : (window.' + token + '))'
        } else {
          conditionalSource = conditionalSource + token
        }
        last = tokens.shift()
      }
    }
  }


  function consumeUntil(tokens, match) {
    let result = ''
    while (tokens.length > 0 && !match.test(tokens[0])) {
      result += tokens.shift()
    }
    return result
  }


  function consumeCSSSelector(tokens) {
    let result
    if (tokens.length > 0 && COMBINED_SELECTOR_START.test(tokens[0])) {
      tokens.shift()
      result = consumeUntil(tokens, COMBINED_SELECTOR_END).trim()
      tokens.shift()
    } else {
      result = consumeUntil(tokens, WHITESPACE_OR_COMMA)
    }
    return result
  }

  const INPUT_SELECTOR = 'input, textarea, select'


  function parseAndCacheTrigger(elt, explicitTrigger, cache) {

    const triggerSpecs = []
    const tokens = tokenizeString(explicitTrigger)
    do {
      consumeUntil(tokens, NOT_WHITESPACE)
      const initialLength = tokens.length
      const trigger = consumeUntil(tokens, /[,\[\s]/)
      if (trigger !== '') {
        if (trigger === 'every') {

          const every = { trigger: 'every' }
          consumeUntil(tokens, NOT_WHITESPACE)
          every.pollInterval = parseInterval(consumeUntil(tokens, /[,\[\s]/))
          consumeUntil(tokens, NOT_WHITESPACE)
          var eventFilter = maybeGenerateConditional(elt, tokens, 'event')
          if (eventFilter) {
            every.eventFilter = eventFilter
          }
          triggerSpecs.push(every)
        } else {

          const triggerSpec = { trigger }
          var eventFilter = maybeGenerateConditional(elt, tokens, 'event')
          if (eventFilter) {
            triggerSpec.eventFilter = eventFilter
          }
          consumeUntil(tokens, NOT_WHITESPACE)
          while (tokens.length > 0 && tokens[0] !== ',') {
            const token = tokens.shift()
            if (token === 'changed') {
              triggerSpec.changed = true
            } else if (token === 'once') {
              triggerSpec.once = true
            } else if (token === 'consume') {
              triggerSpec.consume = true
            } else if (token === 'delay' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec.delay = parseInterval(consumeUntil(tokens, WHITESPACE_OR_COMMA))
            } else if (token === 'from' && tokens[0] === ':') {
              tokens.shift()
              if (COMBINED_SELECTOR_START.test(tokens[0])) {
                var from_arg = consumeCSSSelector(tokens)
              } else {
                var from_arg = consumeUntil(tokens, WHITESPACE_OR_COMMA)
                if (from_arg === 'closest' || from_arg === 'find' || from_arg === 'next' || from_arg === 'previous') {
                  tokens.shift()
                  const selector = consumeCSSSelector(tokens)

                  if (selector.length > 0) {
                    from_arg += ' ' + selector
                  }
                }
              }
              triggerSpec.from = from_arg
            } else if (token === 'target' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec.target = consumeCSSSelector(tokens)
            } else if (token === 'throttle' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec.throttle = parseInterval(consumeUntil(tokens, WHITESPACE_OR_COMMA))
            } else if (token === 'queue' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec.queue = consumeUntil(tokens, WHITESPACE_OR_COMMA)
            } else if (token === 'root' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec[token] = consumeCSSSelector(tokens)
            } else if (token === 'threshold' && tokens[0] === ':') {
              tokens.shift()
              triggerSpec[token] = consumeUntil(tokens, WHITESPACE_OR_COMMA)
            } else {
              triggerErrorEvent(elt, 'htmx:syntax:error', { token: tokens.shift() })
            }
            consumeUntil(tokens, NOT_WHITESPACE)
          }
          triggerSpecs.push(triggerSpec)
        }
      }
      if (tokens.length === initialLength) {
        triggerErrorEvent(elt, 'htmx:syntax:error', { token: tokens.shift() })
      }
      consumeUntil(tokens, NOT_WHITESPACE)
    } while (tokens[0] === ',' && tokens.shift())
    if (cache) {
      cache[explicitTrigger] = triggerSpecs
    }
    return triggerSpecs
  }


  function getTriggerSpecs(elt) {
    const explicitTrigger = getAttributeValue(elt, 'hx-trigger')
    let triggerSpecs = []
    if (explicitTrigger) {
      const cache = htmx.config.triggerSpecsCache
      triggerSpecs = (cache && cache[explicitTrigger]) || parseAndCacheTrigger(elt, explicitTrigger, cache)
    }

    if (triggerSpecs.length > 0) {
      return triggerSpecs
    } else if (matches(elt, 'form')) {
      return [{ trigger: 'submit' }]
    } else if (matches(elt, 'input[type="button"], input[type="submit"]')) {
      return [{ trigger: 'click' }]
    } else if (matches(elt, INPUT_SELECTOR)) {
      return [{ trigger: 'change' }]
    } else {
      return [{ trigger: 'click' }]
    }
  }


  function cancelPolling(elt) {
    getInternalData(elt).cancelled = true
  }


  function processPolling(elt, handler, spec) {
    const nodeData = getInternalData(elt)
    nodeData.timeout = getWindow().setTimeout(function() {
      if (bodyContains(elt) && nodeData.cancelled !== true) {
        if (!maybeFilterEvent(spec, elt, makeEvent('hx:poll:trigger', {
          triggerSpec: spec,
          target: elt
        }))) {
          handler(elt)
        }
        processPolling(elt, handler, spec)
      }
    }, spec.pollInterval)
  }


  function isLocalLink(elt) {
    return location.hostname === elt.hostname &&
      getRawAttribute(elt, 'href') &&
      getRawAttribute(elt, 'href').indexOf('#') !== 0
  }


  function eltIsDisabled(elt) {
    return closest(elt, htmx.config.disableSelector)
  }


  function boostElement(elt, nodeData, triggerSpecs) {
    if ((elt instanceof HTMLAnchorElement && isLocalLink(elt) && (elt.target === '' || elt.target === '_self')) || (elt.tagName === 'FORM' && String(getRawAttribute(elt, 'method')).toLowerCase() !== 'dialog')) {
      nodeData.boosted = true
      let verb, path
      if (elt.tagName === 'A') {
        verb = (('get'))
        path = getRawAttribute(elt, 'href')
      } else {
        const rawAttribute = getRawAttribute(elt, 'method')
        verb = ((rawAttribute ? rawAttribute.toLowerCase() : 'get'))
        path = getRawAttribute(elt, 'action')
        if (path == null || path === '') {


          path = getDocument().location.href
        }
        if (verb === 'get' && path.includes('?')) {
          path = path.replace(/\?[^#]+/, '')
        }
      }
      triggerSpecs.forEach(function(triggerSpec) {
        addEventListener(elt, function(node, evt) {
          const elt = asElement(node)
          if (eltIsDisabled(elt)) {
            cleanUpElement(elt)
            return
          }
          issueAjaxRequest(verb, path, elt, evt)
        }, nodeData, triggerSpec, true)
      })
    }
  }


  function shouldCancel(evt, node) {
    const elt = asElement(node)
    if (!elt) {
      return false
    }
    if (evt.type === 'submit' || evt.type === 'click') {
      if (elt.tagName === 'FORM') {
        return true
      }
      if (matches(elt, 'input[type="submit"], button') &&
        (matches(elt, '[form]') || closest(elt, 'form') !== null)) {
        return true
      }
      if (elt instanceof HTMLAnchorElement && elt.href &&
        (elt.getAttribute('href') === '#' || elt.getAttribute('href').indexOf('#') !== 0)) {
        return true
      }
    }
    return false
  }


  function ignoreBoostedAnchorCtrlClick(elt, evt) {
    return getInternalData(elt).boosted && elt instanceof HTMLAnchorElement && evt.type === 'click' &&

      (evt.ctrlKey || evt.metaKey)
  }


  function maybeFilterEvent(triggerSpec, elt, evt) {
    const eventFilter = triggerSpec.eventFilter
    if (eventFilter) {
      try {
        return eventFilter.call(elt, evt) !== true
      } catch (e) {
        const source = eventFilter.source
        triggerErrorEvent(getDocument().body, 'htmx:eventFilter:error', { error: e, source })
        return true
      }
    }
    return false
  }


  function addEventListener(elt, handler, nodeData, triggerSpec, explicitCancel) {
    const elementData = getInternalData(elt)

    let eltsToListenOn
    if (triggerSpec.from) {
      eltsToListenOn = querySelectorAllExt(elt, triggerSpec.from)
    } else {
      eltsToListenOn = [elt]
    }

    if (triggerSpec.changed) {
      if (!('lastValue' in elementData)) {
        elementData.lastValue = new WeakMap()
      }
      eltsToListenOn.forEach(function(eltToListenOn) {
        if (!elementData.lastValue.has(triggerSpec)) {
          elementData.lastValue.set(triggerSpec, new WeakMap())
        }

        elementData.lastValue.get(triggerSpec).set(eltToListenOn, eltToListenOn.value)
      })
    }
    forEach(eltsToListenOn, function(eltToListenOn) {

      const eventListener = function(evt) {
        if (!bodyContains(elt)) {
          eltToListenOn.removeEventListener(triggerSpec.trigger, eventListener)
          return
        }
        if (ignoreBoostedAnchorCtrlClick(elt, evt)) {
          return
        }
        if (explicitCancel || shouldCancel(evt, elt)) {
          evt.preventDefault()
        }
        if (maybeFilterEvent(triggerSpec, elt, evt)) {
          return
        }
        const eventData = getInternalData(evt)
        eventData.triggerSpec = triggerSpec
        if (eventData.handledFor == null) {
          eventData.handledFor = []
        }
        if (eventData.handledFor.indexOf(elt) < 0) {
          eventData.handledFor.push(elt)
          if (triggerSpec.consume) {
            evt.stopPropagation()
          }
          if (triggerSpec.target && evt.target) {
            if (!matches(asElement(evt.target), triggerSpec.target)) {
              return
            }
          }
          if (triggerSpec.once) {
            if (elementData.triggeredOnce) {
              return
            } else {
              elementData.triggeredOnce = true
            }
          }
          if (triggerSpec.changed) {
            const node = event.target

            const value = node.value
            const lastValue = elementData.lastValue.get(triggerSpec)
            if (lastValue.has(node) && lastValue.get(node) === value) {
              return
            }
            lastValue.set(node, value)
          }
          if (elementData.delayed) {
            clearTimeout(elementData.delayed)
          }
          if (elementData.throttle) {
            return
          }

          if (triggerSpec.throttle > 0) {
            if (!elementData.throttle) {
              triggerEvent(elt, 'htmx:trigger')
              handler(elt, evt)
              elementData.throttle = getWindow().setTimeout(function() {
                elementData.throttle = null
              }, triggerSpec.throttle)
            }
          } else if (triggerSpec.delay > 0) {
            elementData.delayed = getWindow().setTimeout(function() {
              triggerEvent(elt, 'htmx:trigger')
              handler(elt, evt)
            }, triggerSpec.delay)
          } else {
            triggerEvent(elt, 'htmx:trigger')
            handler(elt, evt)
          }
        }
      }
      if (nodeData.listenerInfos == null) {
        nodeData.listenerInfos = []
      }
      nodeData.listenerInfos.push({
        trigger: triggerSpec.trigger,
        listener: eventListener,
        on: eltToListenOn
      })
      eltToListenOn.addEventListener(triggerSpec.trigger, eventListener)
    })
  }

  let windowIsScrolling = false
  let scrollHandler = null
  function initScrollHandler() {
    if (!scrollHandler) {
      scrollHandler = function() {
        windowIsScrolling = true
      }
      window.addEventListener('scroll', scrollHandler)
      window.addEventListener('resize', scrollHandler)
      setInterval(function() {
        if (windowIsScrolling) {
          windowIsScrolling = false
          forEach(getDocument().querySelectorAll("[hx-trigger*='revealed'],[data-hx-trigger*='revealed']"), function(elt) {
            maybeReveal(elt)
          })
        }
      }, 200)
    }
  }


  function maybeReveal(elt) {
    if (!hasAttribute(elt, 'data-hx-revealed') && isScrolledIntoView(elt)) {
      elt.setAttribute('data-hx-revealed', 'true')
      const nodeData = getInternalData(elt)
      if (nodeData.initHash) {
        triggerEvent(elt, 'revealed')
      } else {

        elt.addEventListener('htmx:afterProcessNode', function() { triggerEvent(elt, 'revealed') }, { once: true })
      }
    }
  }




  function loadImmediately(elt, handler, nodeData, delay) {
    const load = function() {
      if (!nodeData.loaded) {
        nodeData.loaded = true
        triggerEvent(elt, 'htmx:trigger')
        handler(elt)
      }
    }
    if (delay > 0) {
      getWindow().setTimeout(load, delay)
    } else {
      load()
    }
  }


  function processVerbs(elt, nodeData, triggerSpecs) {
    let explicitAction = false
    forEach(VERBS, function(verb) {
      if (hasAttribute(elt, 'hx-' + verb)) {
        const path = getAttributeValue(elt, 'hx-' + verb)
        explicitAction = true
        nodeData.path = path
        nodeData.verb = verb
        triggerSpecs.forEach(function(triggerSpec) {
          addTriggerHandler(elt, triggerSpec, nodeData, function(node, evt) {
            const elt = asElement(node)
            if (closest(elt, htmx.config.disableSelector)) {
              cleanUpElement(elt)
              return
            }
            issueAjaxRequest(verb, path, elt, evt)
          })
        })
      }
    })
    return explicitAction
  }




  function addTriggerHandler(elt, triggerSpec, nodeData, handler) {
    if (triggerSpec.trigger === 'revealed') {
      initScrollHandler()
      addEventListener(elt, handler, nodeData, triggerSpec)
      maybeReveal(asElement(elt))
    } else if (triggerSpec.trigger === 'intersect') {
      const observerOptions = {}
      if (triggerSpec.root) {
        observerOptions.root = querySelectorExt(elt, triggerSpec.root)
      }
      if (triggerSpec.threshold) {
        observerOptions.threshold = parseFloat(triggerSpec.threshold)
      }
      const observer = new IntersectionObserver(function(entries) {
        for (let i = 0; i < entries.length; i++) {
          const entry = entries[i]
          if (entry.isIntersecting) {
            triggerEvent(elt, 'intersect')
            break
          }
        }
      }, observerOptions)
      observer.observe(asElement(elt))
      addEventListener(asElement(elt), handler, nodeData, triggerSpec)
    } else if (!nodeData.firstInitCompleted && triggerSpec.trigger === 'load') {
      if (!maybeFilterEvent(triggerSpec, elt, makeEvent('load', { elt }))) {
        loadImmediately(asElement(elt), handler, nodeData, triggerSpec.delay)
      }
    } else if (triggerSpec.pollInterval > 0) {
      nodeData.polling = true
      processPolling(asElement(elt), handler, triggerSpec)
    } else {
      addEventListener(elt, handler, nodeData, triggerSpec)
    }
  }


  function shouldProcessHxOn(node) {
    const elt = asElement(node)
    if (!elt) {
      return false
    }
    const attributes = elt.attributes
    for (let j = 0; j < attributes.length; j++) {
      const attrName = attributes[j].name
      if (startsWith(attrName, 'hx-on:') || startsWith(attrName, 'data-hx-on:') ||
        startsWith(attrName, 'hx-on-') || startsWith(attrName, 'data-hx-on-')) {
        return true
      }
    }
    return false
  }


  const HX_ON_QUERY = new XPathEvaluator()
    .createExpression('./
    const elements = []
    if (elt instanceof DocumentFragment) {
      for (const child of elt.childNodes) {
        processHXOnRoot(child, elements)
      }
    } else {
      processHXOnRoot(elt, elements)
    }
    return elements
  }


  function findElementsToProcess(elt) {
    if (elt.querySelectorAll) {
      const boostedSelector = ', [hx-boost] a, [data-hx-boost] a, a[hx-boost], a[data-hx-boost]'

      const extensionSelectors = []
      for (const e in extensions) {
        const extension = extensions[e]
        if (extension.getSelectors) {
          var selectors = extension.getSelectors()
          if (selectors) {
            extensionSelectors.push(selectors)
          }
        }
      }

      const results = elt.querySelectorAll(VERB_SELECTOR + boostedSelector + ", form, [type='submit']," +
        ' [hx-ext], [data-hx-ext], [hx-trigger], [data-hx-trigger]' + extensionSelectors.flat().map(s => ', ' + s).join(''))

      return results
    } else {
      return []
    }
  }


  function maybeSetLastButtonClicked(evt) {
    const elt =  (closest(asElement(evt.target), "button, input[type='submit']"))
    const internalData = getRelatedFormData(evt)
    if (internalData) {
      internalData.lastButtonClicked = elt
    }
  }


  function maybeUnsetLastButtonClicked(evt) {
    const internalData = getRelatedFormData(evt)
    if (internalData) {
      internalData.lastButtonClicked = null
    }
  }


  function getRelatedFormData(evt) {
    const elt = closest(asElement(evt.target), "button, input[type='submit']")
    if (!elt) {
      return
    }
    const form = resolveTarget('#' + getRawAttribute(elt, 'form'), elt.getRootNode()) || closest(elt, 'form')
    if (!form) {
      return
    }
    return getInternalData(form)
  }


  function initButtonTracking(elt) {



    elt.addEventListener('click', maybeSetLastButtonClicked)
    elt.addEventListener('focusin', maybeSetLastButtonClicked)
    elt.addEventListener('focusout', maybeUnsetLastButtonClicked)
  }


  function addHxOnEventHandler(elt, eventName, code) {
    const nodeData = getInternalData(elt)
    if (!Array.isArray(nodeData.onHandlers)) {
      nodeData.onHandlers = []
    }
    let func

    const listener = function(e) {
      maybeEval(elt, function() {
        if (eltIsDisabled(elt)) {
          return
        }
        if (!func) {
          func = new Function('event', code)
        }
        func.call(elt, e)
      })
    }
    elt.addEventListener(eventName, listener)
    nodeData.onHandlers.push({ event: eventName, listener })
  }


  function processHxOnWildcard(elt) {

    deInitOnHandlers(elt)

    for (let i = 0; i < elt.attributes.length; i++) {
      const name = elt.attributes[i].name
      const value = elt.attributes[i].value
      if (startsWith(name, 'hx-on') || startsWith(name, 'data-hx-on')) {
        const afterOnPosition = name.indexOf('-on') + 3
        const nextChar = name.slice(afterOnPosition, afterOnPosition + 1)
        if (nextChar === '-' || nextChar === ':') {
          let eventName = name.slice(afterOnPosition + 1)

          if (startsWith(eventName, ':')) {
            eventName = 'htmx' + eventName
          } else if (startsWith(eventName, '-')) {
            eventName = 'htmx:' + eventName.slice(1)
          } else if (startsWith(eventName, 'htmx-')) {
            eventName = 'htmx:' + eventName.slice(5)
          }

          addHxOnEventHandler(elt, eventName, value)
        }
      }
    }
  }


  function initNode(elt) {
    if (closest(elt, htmx.config.disableSelector)) {
      cleanUpElement(elt)
      return
    }
    const nodeData = getInternalData(elt)
    const attrHash = attributeHash(elt)
    if (nodeData.initHash !== attrHash) {

      deInitNode(elt)

      nodeData.initHash = attrHash

      triggerEvent(elt, 'htmx:beforeProcessNode')

      const triggerSpecs = getTriggerSpecs(elt)
      const hasExplicitHttpAction = processVerbs(elt, nodeData, triggerSpecs)

      if (!hasExplicitHttpAction) {
        if (getClosestAttributeValue(elt, 'hx-boost') === 'true') {
          boostElement(elt, nodeData, triggerSpecs)
        } else if (hasAttribute(elt, 'hx-trigger')) {
          triggerSpecs.forEach(function(triggerSpec) {

            addTriggerHandler(elt, triggerSpec, nodeData, function() {
            })
          })
        }
      }



      if (elt.tagName === 'FORM' || (getRawAttribute(elt, 'type') === 'submit' && hasAttribute(elt, 'form'))) {
        initButtonTracking(elt)
      }

      nodeData.firstInitCompleted = true
      triggerEvent(elt, 'htmx:afterProcessNode')
    }
  }


  function processNode(elt) {
    elt = resolveTarget(elt)
    if (closest(elt, htmx.config.disableSelector)) {
      cleanUpElement(elt)
      return
    }
    initNode(elt)
    forEach(findElementsToProcess(elt), function(child) { initNode(child) })
    forEach(findHxOnWildcardElements(elt), processHxOnWildcard)
  }






  function kebabEventName(str) {
    return str.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
  }


  function makeEvent(eventName, detail) {
    let evt
    if (window.CustomEvent && typeof window.CustomEvent === 'function') {


      evt = new CustomEvent(eventName, { bubbles: true, cancelable: true, composed: true, detail })
    } else {
      evt = getDocument().createEvent('CustomEvent')
      evt.initCustomEvent(eventName, true, true, detail)
    }
    return evt
  }


  function triggerErrorEvent(elt, eventName, detail) {
    triggerEvent(elt, eventName, mergeObjects({ error: eventName }, detail))
  }


  function ignoreEventForLogging(eventName) {
    return eventName === 'htmx:afterProcessNode'
  }


  function withExtensions(elt, toDo) {
    forEach(getExtensions(elt), function(extension) {
      try {
        toDo(extension)
      } catch (e) {
        logError(e)
      }
    })
  }

  function logError(msg) {
    if (console.error) {
      console.error(msg)
    } else if (console.log) {
      console.log('ERROR: ', msg)
    }
  }


  function triggerEvent(elt, eventName, detail) {
    elt = resolveTarget(elt)
    if (detail == null) {
      detail = {}
    }
    detail.elt = elt
    const event = makeEvent(eventName, detail)
    if (htmx.logger && !ignoreEventForLogging(eventName)) {
      htmx.logger(elt, eventName, detail)
    }
    if (detail.error) {
      logError(detail.error)
      triggerEvent(elt, 'htmx:error', { errorInfo: detail })
    }
    let eventResult = elt.dispatchEvent(event)
    const kebabName = kebabEventName(eventName)
    if (eventResult && kebabName !== eventName) {
      const kebabedEvent = makeEvent(kebabName, event.detail)
      eventResult = eventResult && elt.dispatchEvent(kebabedEvent)
    }
    withExtensions(asElement(elt), function(extension) {
      eventResult = eventResult && (extension.onEvent(eventName, event) !== false && !event.defaultPrevented)
    })
    return eventResult
  }




  let currentPathForHistory = location.pathname + location.search


  function getHistoryElement() {
    const historyElt = getDocument().querySelector('[hx-history-elt],[data-hx-history-elt]')
    return historyElt || getDocument().body
  }


  function saveToHistoryCache(url, rootElt) {
    if (!canAccessLocalStorage()) {
      return
    }


    const innerHTML = cleanInnerHtmlForHistory(rootElt)
    const title = getDocument().title
    const scroll = window.scrollY

    if (htmx.config.historyCacheSize <= 0) {

      localStorage.removeItem('htmx-history-cache')
      return
    }

    url = normalizePath(url)

    const historyCache = parseJSON(localStorage.getItem('htmx-history-cache')) || []
    for (let i = 0; i < historyCache.length; i++) {
      if (historyCache[i].url === url) {
        historyCache.splice(i, 1)
        break
      }
    }


    const newHistoryItem = { url, content: innerHTML, title, scroll }

    triggerEvent(getDocument().body, 'htmx:historyItemCreated', { item: newHistoryItem, cache: historyCache })

    historyCache.push(newHistoryItem)
    while (historyCache.length > htmx.config.historyCacheSize) {
      historyCache.shift()
    }


    while (historyCache.length > 0) {
      try {
        localStorage.setItem('htmx-history-cache', JSON.stringify(historyCache))
        break
      } catch (e) {
        triggerErrorEvent(getDocument().body, 'htmx:historyCacheError', { cause: e, cache: historyCache })
        historyCache.shift()
      }
    }
  }




  function getCachedHistory(url) {
    if (!canAccessLocalStorage()) {
      return null
    }

    url = normalizePath(url)

    const historyCache = parseJSON(localStorage.getItem('htmx-history-cache')) || []
    for (let i = 0; i < historyCache.length; i++) {
      if (historyCache[i].url === url) {
        return historyCache[i]
      }
    }
    return null
  }


  function cleanInnerHtmlForHistory(elt) {
    const className = htmx.config.requestClass
    const clone =  (elt.cloneNode(true))
    forEach(findAll(clone, '.' + className), function(child) {
      removeClassFromElement(child, className)
    })

    forEach(findAll(clone, '[data-disabled-by-htmx]'), function(child) {
      child.removeAttribute('disabled')
    })
    return clone.innerHTML
  }

  function saveCurrentPageToHistory() {
    const elt = getHistoryElement()
    const path = currentPathForHistory || location.pathname + location.search






    let disableHistoryCache
    try {
      disableHistoryCache = getDocument().querySelector('[hx-history="false" i],[data-hx-history="false" i]')
    } catch (e) {

      disableHistoryCache = getDocument().querySelector('[hx-history="false"],[data-hx-history="false"]')
    }
    if (!disableHistoryCache) {
      triggerEvent(getDocument().body, 'htmx:beforeHistorySave', { path, historyElt: elt })
      saveToHistoryCache(path, elt)
    }

    if (htmx.config.historyEnabled) history.replaceState({ htmx: true }, getDocument().title, window.location.href)
  }


  function pushUrlIntoHistory(path) {

    if (htmx.config.getCacheBusterParam) {
      path = path.replace(/org\.htmx\.cache-buster=[^&]*&?/, '')
      if (endsWith(path, '&') || endsWith(path, '?')) {
        path = path.slice(0, -1)
      }
    }
    if (htmx.config.historyEnabled) {
      history.pushState({ htmx: true }, '', path)
    }
    currentPathForHistory = path
  }


  function replaceUrlInHistory(path) {
    if (htmx.config.historyEnabled) history.replaceState({ htmx: true }, '', path)
    currentPathForHistory = path
  }


  function settleImmediately(tasks) {
    forEach(tasks, function(task) {
      task.call(undefined)
    })
  }


  function loadHistoryFromServer(path) {
    const request = new XMLHttpRequest()
    const details = { path, xhr: request }
    triggerEvent(getDocument().body, 'htmx:historyCacheMiss', details)
    request.open('GET', path, true)
    request.setRequestHeader('HX-Request', 'true')
    request.setRequestHeader('HX-History-Restore-Request', 'true')
    request.setRequestHeader('HX-Current-URL', getDocument().location.href)
    request.onload = function() {
      if (this.status >= 200 && this.status < 400) {
        triggerEvent(getDocument().body, 'htmx:historyCacheMissLoad', details)
        const fragment = makeFragment(this.response)

        const content = fragment.querySelector('[hx-history-elt],[data-hx-history-elt]') || fragment
        const historyElement = getHistoryElement()
        const settleInfo = makeSettleInfo(historyElement)
        handleTitle(fragment.title)

        handlePreservedElements(fragment)
        swapInnerHTML(historyElement, content, settleInfo)
        restorePreservedElements()
        settleImmediately(settleInfo.tasks)
        currentPathForHistory = path
        triggerEvent(getDocument().body, 'htmx:historyRestore', { path, cacheMiss: true, serverResponse: this.response })
      } else {
        triggerErrorEvent(getDocument().body, 'htmx:historyCacheMissLoadError', details)
      }
    }
    request.send()
  }


  function restoreHistory(path) {
    saveCurrentPageToHistory()
    path = path || location.pathname + location.search
    const cached = getCachedHistory(path)
    if (cached) {
      const fragment = makeFragment(cached.content)
      const historyElement = getHistoryElement()
      const settleInfo = makeSettleInfo(historyElement)
      handleTitle(cached.title)
      handlePreservedElements(fragment)
      swapInnerHTML(historyElement, fragment, settleInfo)
      restorePreservedElements()
      settleImmediately(settleInfo.tasks)
      getWindow().setTimeout(function() {
        window.scrollTo(0, cached.scroll)
      }, 0)
      currentPathForHistory = path
      triggerEvent(getDocument().body, 'htmx:historyRestore', { path, item: cached })
    } else {
      if (htmx.config.refreshOnHistoryMiss) {


        window.location.reload(true)
      } else {
        loadHistoryFromServer(path)
      }
    }
  }


  function addRequestIndicatorClasses(elt) {
    let indicators =  (findAttributeTargets(elt, 'hx-indicator'))
    if (indicators == null) {
      indicators = [elt]
    }
    forEach(indicators, function(ic) {
      const internalData = getInternalData(ic)
      internalData.requestCount = (internalData.requestCount || 0) + 1
      ic.classList.add.call(ic.classList, htmx.config.requestClass)
    })
    return indicators
  }


  function disableElements(elt) {
    let disabledElts =  (findAttributeTargets(elt, 'hx-disabled-elt'))
    if (disabledElts == null) {
      disabledElts = []
    }
    forEach(disabledElts, function(disabledElement) {
      const internalData = getInternalData(disabledElement)
      internalData.requestCount = (internalData.requestCount || 0) + 1
      disabledElement.setAttribute('disabled', '')
      disabledElement.setAttribute('data-disabled-by-htmx', '')
    })
    return disabledElts
  }


  function removeRequestIndicators(indicators, disabled) {
    forEach(indicators.concat(disabled), function(ele) {
      const internalData = getInternalData(ele)
      internalData.requestCount = (internalData.requestCount || 1) - 1
    })
    forEach(indicators, function(ic) {
      const internalData = getInternalData(ic)
      if (internalData.requestCount === 0) {
        ic.classList.remove.call(ic.classList, htmx.config.requestClass)
      }
    })
    forEach(disabled, function(disabledElement) {
      const internalData = getInternalData(disabledElement)
      if (internalData.requestCount === 0) {
        disabledElement.removeAttribute('disabled')
        disabledElement.removeAttribute('data-disabled-by-htmx')
      }
    })
  }






  function haveSeenNode(processed, elt) {
    for (let i = 0; i < processed.length; i++) {
      const node = processed[i]
      if (node.isSameNode(elt)) {
        return true
      }
    }
    return false
  }


  function shouldInclude(element) {

    const elt =  (element)
    if (elt.name === '' || elt.name == null || elt.disabled || closest(elt, 'fieldset[disabled]')) {
      return false
    }

    if (elt.type === 'button' || elt.type === 'submit' || elt.tagName === 'image' || elt.tagName === 'reset' || elt.tagName === 'file') {
      return false
    }
    if (elt.type === 'checkbox' || elt.type === 'radio') {
      return elt.checked
    }
    return true
  }


  function addValueToFormData(name, value, formData) {
    if (name != null && value != null) {
      if (Array.isArray(value)) {
        value.forEach(function(v) { formData.append(name, v) })
      } else {
        formData.append(name, value)
      }
    }
  }


  function removeValueFromFormData(name, value, formData) {
    if (name != null && value != null) {
      let values = formData.getAll(name)
      if (Array.isArray(value)) {
        values = values.filter(v => value.indexOf(v) < 0)
      } else {
        values = values.filter(v => v !== value)
      }
      formData.delete(name)
      forEach(values, v => formData.append(name, v))
    }
  }


  function processInputValue(processed, formData, errors, elt, validate) {
    if (elt == null || haveSeenNode(processed, elt)) {
      return
    } else {
      processed.push(elt)
    }
    if (shouldInclude(elt)) {
      const name = getRawAttribute(elt, 'name')

      let value = elt.value
      if (elt instanceof HTMLSelectElement && elt.multiple) {
        value = toArray(elt.querySelectorAll('option:checked')).map(function(e) { return ((e)).value })
      }

      if (elt instanceof HTMLInputElement && elt.files) {
        value = toArray(elt.files)
      }
      addValueToFormData(name, value, formData)
      if (validate) {
        validateElement(elt, errors)
      }
    }
    if (elt instanceof HTMLFormElement) {
      forEach(elt.elements, function(input) {
        if (processed.indexOf(input) >= 0) {



          removeValueFromFormData(input.name, input.value, formData)
        } else {
          processed.push(input)
        }
        if (validate) {
          validateElement(input, errors)
        }
      })
      new FormData(elt).forEach(function(value, name) {
        if (value instanceof File && value.name === '') {
          return
        }
        addValueToFormData(name, value, formData)
      })
    }
  }


  function validateElement(elt, errors) {
    const element =  (elt)
    if (element.willValidate) {
      triggerEvent(element, 'htmx:validation:validate')
      if (!element.checkValidity()) {
        errors.push({ elt: element, message: element.validationMessage, validity: element.validity })
        triggerEvent(element, 'htmx:validation:failed', { message: element.validationMessage, validity: element.validity })
      }
    }
  }


  function overrideFormData(receiver, donor) {
    for (const key of donor.keys()) {
      receiver.delete(key)
    }
    donor.forEach(function(value, key) {
      receiver.append(key, value)
    })
    return receiver
  }


  function getInputValues(elt, verb) {

    const processed = []
    const formData = new FormData()
    const priorityFormData = new FormData()

    const errors = []
    const internalData = getInternalData(elt)
    if (internalData.lastButtonClicked && !bodyContains(internalData.lastButtonClicked)) {
      internalData.lastButtonClicked = null
    }



    let validate = (elt instanceof HTMLFormElement && elt.noValidate !== true) || getAttributeValue(elt, 'hx-validate') === 'true'
    if (internalData.lastButtonClicked) {
      validate = validate && internalData.lastButtonClicked.formNoValidate !== true
    }


    if (verb !== 'get') {
      processInputValue(processed, priorityFormData, errors, closest(elt, 'form'), validate)
    }


    processInputValue(processed, formData, errors, elt, validate)


    if (internalData.lastButtonClicked || elt.tagName === 'BUTTON' ||
    (elt.tagName === 'INPUT' && getRawAttribute(elt, 'type') === 'submit')) {
      const button = internalData.lastButtonClicked || ((elt))
      const name = getRawAttribute(button, 'name')
      addValueToFormData(name, button.value, priorityFormData)
    }


    const includes = findAttributeTargets(elt, 'hx-include')
    forEach(includes, function(node) {
      processInputValue(processed, formData, errors, asElement(node), validate)

      if (!matches(node, 'form')) {
        forEach(asParentNode(node).querySelectorAll(INPUT_SELECTOR), function(descendant) {
          processInputValue(processed, formData, errors, descendant, validate)
        })
      }
    })


    overrideFormData(formData, priorityFormData)

    return { errors, formData, values: formDataProxy(formData) }
  }


  function appendParam(returnStr, name, realValue) {
    if (returnStr !== '') {
      returnStr += '&'
    }
    if (String(realValue) === '[object Object]') {
      realValue = JSON.stringify(realValue)
    }
    const s = encodeURIComponent(realValue)
    returnStr += encodeURIComponent(name) + '=' + s
    return returnStr
  }


  function urlEncode(values) {
    values = formDataFromObject(values)
    let returnStr = ''
    values.forEach(function(value, key) {
      returnStr = appendParam(returnStr, key, value)
    })
    return returnStr
  }






  function getHeaders(elt, target, prompt) {

    const headers = {
      'HX-Request': 'true',
      'HX-Trigger': getRawAttribute(elt, 'id'),
      'HX-Trigger-Name': getRawAttribute(elt, 'name'),
      'HX-Target': getAttributeValue(target, 'id'),
      'HX-Current-URL': getDocument().location.href
    }
    getValuesForElement(elt, 'hx-headers', false, headers)
    if (prompt !== undefined) {
      headers['HX-Prompt'] = prompt
    }
    if (getInternalData(elt).boosted) {
      headers['HX-Boosted'] = 'true'
    }
    return headers
  }


  function filterValues(inputValues, elt) {
    const paramsValue = getClosestAttributeValue(elt, 'hx-params')
    if (paramsValue) {
      if (paramsValue === 'none') {
        return new FormData()
      } else if (paramsValue === '*') {
        return inputValues
      } else if (paramsValue.indexOf('not ') === 0) {
        forEach(paramsValue.slice(4).split(','), function(name) {
          name = name.trim()
          inputValues.delete(name)
        })
        return inputValues
      } else {
        const newValues = new FormData()
        forEach(paramsValue.split(','), function(name) {
          name = name.trim()
          if (inputValues.has(name)) {
            inputValues.getAll(name).forEach(function(value) { newValues.append(name, value) })
          }
        })
        return newValues
      }
    } else {
      return inputValues
    }
  }


  function isAnchorLink(elt) {
    return !!getRawAttribute(elt, 'href') && getRawAttribute(elt, 'href').indexOf('#') >= 0
  }


  function getSwapSpecification(elt, swapInfoOverride) {
    const swapInfo = swapInfoOverride || getClosestAttributeValue(elt, 'hx-swap')

    const swapSpec = {
      swapStyle: getInternalData(elt).boosted ? 'innerHTML' : htmx.config.defaultSwapStyle,
      swapDelay: htmx.config.defaultSwapDelay,
      settleDelay: htmx.config.defaultSettleDelay
    }
    if (htmx.config.scrollIntoViewOnBoost && getInternalData(elt).boosted && !isAnchorLink(elt)) {
      swapSpec.show = 'top'
    }
    if (swapInfo) {
      const split = splitOnWhitespace(swapInfo)
      if (split.length > 0) {
        for (let i = 0; i < split.length; i++) {
          const value = split[i]
          if (value.indexOf('swap:') === 0) {
            swapSpec.swapDelay = parseInterval(value.slice(5))
          } else if (value.indexOf('settle:') === 0) {
            swapSpec.settleDelay = parseInterval(value.slice(7))
          } else if (value.indexOf('transition:') === 0) {
            swapSpec.transition = value.slice(11) === 'true'
          } else if (value.indexOf('ignoreTitle:') === 0) {
            swapSpec.ignoreTitle = value.slice(12) === 'true'
          } else if (value.indexOf('scroll:') === 0) {
            const scrollSpec = value.slice(7)
            var splitSpec = scrollSpec.split(':')
            const scrollVal = splitSpec.pop()
            var selectorVal = splitSpec.length > 0 ? splitSpec.join(':') : null

            swapSpec.scroll = scrollVal
            swapSpec.scrollTarget = selectorVal
          } else if (value.indexOf('show:') === 0) {
            const showSpec = value.slice(5)
            var splitSpec = showSpec.split(':')
            const showVal = splitSpec.pop()
            var selectorVal = splitSpec.length > 0 ? splitSpec.join(':') : null
            swapSpec.show = showVal
            swapSpec.showTarget = selectorVal
          } else if (value.indexOf('focus-scroll:') === 0) {
            const focusScrollVal = value.slice('focus-scroll:'.length)
            swapSpec.focusScroll = focusScrollVal == 'true'
          } else if (i == 0) {
            swapSpec.swapStyle = value
          } else {
            logError('Unknown modifier in hx-swap: ' + value)
          }
        }
      }
    }
    return swapSpec
  }


  function usesFormData(elt) {
    return getClosestAttributeValue(elt, 'hx-encoding') === 'multipart/form-data' ||
    (matches(elt, 'form') && getRawAttribute(elt, 'enctype') === 'multipart/form-data')
  }


  function encodeParamsForBody(xhr, elt, filteredParameters) {
    let encodedParameters = null
    withExtensions(elt, function(extension) {
      if (encodedParameters == null) {
        encodedParameters = extension.encodeParameters(xhr, filteredParameters, elt)
      }
    })
    if (encodedParameters != null) {
      return encodedParameters
    } else {
      if (usesFormData(elt)) {


        return overrideFormData(new FormData(), formDataFromObject(filteredParameters))
      } else {
        return urlEncode(filteredParameters)
      }
    }
  }


  function makeSettleInfo(target) {
    return { tasks: [], elts: [target] }
  }


  function updateScrollState(content, swapSpec) {
    const first = content[0]
    const last = content[content.length - 1]
    if (swapSpec.scroll) {
      var target = null
      if (swapSpec.scrollTarget) {
        target = asElement(querySelectorExt(first, swapSpec.scrollTarget))
      }
      if (swapSpec.scroll === 'top' && (first || target)) {
        target = target || first
        target.scrollTop = 0
      }
      if (swapSpec.scroll === 'bottom' && (last || target)) {
        target = target || last
        target.scrollTop = target.scrollHeight
      }
    }
    if (swapSpec.show) {
      var target = null
      if (swapSpec.showTarget) {
        let targetStr = swapSpec.showTarget
        if (swapSpec.showTarget === 'window') {
          targetStr = 'body'
        }
        target = asElement(querySelectorExt(first, targetStr))
      }
      if (swapSpec.show === 'top' && (first || target)) {
        target = target || first

        target.scrollIntoView({ block: 'start', behavior: htmx.config.scrollBehavior })
      }
      if (swapSpec.show === 'bottom' && (last || target)) {
        target = target || last

        target.scrollIntoView({ block: 'end', behavior: htmx.config.scrollBehavior })
      }
    }
  }


  function getValuesForElement(elt, attr, evalAsDefault, values) {
    if (values == null) {
      values = {}
    }
    if (elt == null) {
      return values
    }
    const attributeValue = getAttributeValue(elt, attr)
    if (attributeValue) {
      let str = attributeValue.trim()
      let evaluateValue = evalAsDefault
      if (str === 'unset') {
        return null
      }
      if (str.indexOf('javascript:') === 0) {
        str = str.slice(11)
        evaluateValue = true
      } else if (str.indexOf('js:') === 0) {
        str = str.slice(3)
        evaluateValue = true
      }
      if (str.indexOf('{') !== 0) {
        str = '{' + str + '}'
      }
      let varsValues
      if (evaluateValue) {
        varsValues = maybeEval(elt, function() { return Function('return (' + str + ')')() }, {})
      } else {
        varsValues = parseJSON(str)
      }
      for (const key in varsValues) {
        if (varsValues.hasOwnProperty(key)) {
          if (values[key] == null) {
            values[key] = varsValues[key]
          }
        }
      }
    }
    return getValuesForElement(asElement(parentElt(elt)), attr, evalAsDefault, values)
  }


  function maybeEval(elt, toEval, defaultVal) {
    if (htmx.config.allowEval) {
      return toEval()
    } else {
      triggerErrorEvent(elt, 'htmx:evalDisallowedError')
      return defaultVal
    }
  }


  function getHXVarsForElement(elt, expressionVars) {
    return getValuesForElement(elt, 'hx-vars', true, expressionVars)
  }


  function getHXValsForElement(elt, expressionVars) {
    return getValuesForElement(elt, 'hx-vals', false, expressionVars)
  }


  function getExpressionVars(elt) {
    return mergeObjects(getHXVarsForElement(elt), getHXValsForElement(elt))
  }


  function safelySetHeaderValue(xhr, header, headerValue) {
    if (headerValue !== null) {
      try {
        xhr.setRequestHeader(header, headerValue)
      } catch (e) {

        xhr.setRequestHeader(header, encodeURIComponent(headerValue))
        xhr.setRequestHeader(header + '-URI-AutoEncoded', 'true')
      }
    }
  }


  function getPathFromResponse(xhr) {

    if (xhr.responseURL && typeof (URL) !== 'undefined') {
      try {
        const url = new URL(xhr.responseURL)
        return url.pathname + url.search
      } catch (e) {
        triggerErrorEvent(getDocument().body, 'htmx:badResponseUrl', { url: xhr.responseURL })
      }
    }
  }


  function hasHeader(xhr, regexp) {
    return regexp.test(xhr.getAllResponseHeaders())
  }


  function ajaxHelper(verb, path, context) {
    verb = ((verb.toLowerCase()))
    if (context) {
      if (context instanceof Element || typeof context === 'string') {
        return issueAjaxRequest(verb, path, null, null, {
          targetOverride: resolveTarget(context) || DUMMY_ELT,
          returnPromise: true
        })
      } else {
        let resolvedTarget = resolveTarget(context.target)


        if ((context.target && !resolvedTarget) || (context.source && !resolvedTarget && !resolveTarget(context.source))) {
          resolvedTarget = DUMMY_ELT
        }
        return issueAjaxRequest(verb, path, resolveTarget(context.source), context.event,
          {
            handler: context.handler,
            headers: context.headers,
            values: context.values,
            targetOverride: resolvedTarget,
            swapOverride: context.swap,
            select: context.select,
            returnPromise: true
          })
      }
    } else {
      return issueAjaxRequest(verb, path, null, null, {
        returnPromise: true
      })
    }
  }


  function hierarchyForElt(elt) {
    const arr = []
    while (elt) {
      arr.push(elt)
      elt = elt.parentElement
    }
    return arr
  }


  function verifyPath(elt, path, requestConfig) {
    let sameHost
    let url
    if (typeof URL === 'function') {
      url = new URL(path, document.location.href)
      const origin = document.location.origin
      sameHost = origin === url.origin
    } else {

      url = path
      sameHost = startsWith(path, document.location.origin)
    }

    if (htmx.config.selfRequestsOnly) {
      if (!sameHost) {
        return false
      }
    }
    return triggerEvent(elt, 'htmx:validateUrl', mergeObjects({ url, sameHost }, requestConfig))
  }


  function formDataFromObject(obj) {
    if (obj instanceof FormData) return obj
    const formData = new FormData()
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        if (obj[key] && typeof obj[key].forEach === 'function') {
          obj[key].forEach(function(v) { formData.append(key, v) })
        } else if (typeof obj[key] === 'object' && !(obj[key] instanceof Blob)) {
          formData.append(key, JSON.stringify(obj[key]))
        } else {
          formData.append(key, obj[key])
        }
      }
    }
    return formData
  }


  function formDataArrayProxy(formData, name, array) {

    return new Proxy(array, {
      get: function(target, key) {
        if (typeof key === 'number') return target[key]
        if (key === 'length') return target.length
        if (key === 'push') {
          return function(value) {
            target.push(value)
            formData.append(name, value)
          }
        }
        if (typeof target[key] === 'function') {
          return function() {
            target[key].apply(target, arguments)
            formData.delete(name)
            target.forEach(function(v) { formData.append(name, v) })
          }
        }

        if (target[key] && target[key].length === 1) {
          return target[key][0]
        } else {
          return target[key]
        }
      },
      set: function(target, index, value) {
        target[index] = value
        formData.delete(name)
        target.forEach(function(v) { formData.append(name, v) })
        return true
      }
    })
  }


  function formDataProxy(formData) {
    return new Proxy(formData, {
      get: function(target, name) {
        if (typeof name === 'symbol') {

          const result = Reflect.get(target, name)

          if (typeof result === 'function') {
            return function() {
              return result.apply(formData, arguments)
            }
          } else {
            return result
          }
        }
        if (name === 'toJSON') {

          return () => Object.fromEntries(formData)
        }
        if (name in target) {

          if (typeof target[name] === 'function') {
            return function() {
              return formData[name].apply(formData, arguments)
            }
          } else {
            return target[name]
          }
        }
        const array = formData.getAll(name)

        if (array.length === 0) {
          return undefined
        } else if (array.length === 1) {
          return array[0]
        } else {
          return formDataArrayProxy(target, name, array)
        }
      },
      set: function(target, name, value) {
        if (typeof name !== 'string') {
          return false
        }
        target.delete(name)
        if (value && typeof value.forEach === 'function') {
          value.forEach(function(v) { target.append(name, v) })
        } else if (typeof value === 'object' && !(value instanceof Blob)) {
          target.append(name, JSON.stringify(value))
        } else {
          target.append(name, value)
        }
        return true
      },
      deleteProperty: function(target, name) {
        if (typeof name === 'string') {
          target.delete(name)
        }
        return true
      },

      ownKeys: function(target) {
        return Reflect.ownKeys(Object.fromEntries(target))
      },
      getOwnPropertyDescriptor: function(target, prop) {
        return Reflect.getOwnPropertyDescriptor(Object.fromEntries(target), prop)
      }
    })
  }


  function issueAjaxRequest(verb, path, elt, event, etc, confirmed) {
    let resolve = null
    let reject = null
    etc = etc != null ? etc : {}
    if (etc.returnPromise && typeof Promise !== 'undefined') {
      var promise = new Promise(function(_resolve, _reject) {
        resolve = _resolve
        reject = _reject
      })
    }
    if (elt == null) {
      elt = getDocument().body
    }
    const responseHandler = etc.handler || handleAjaxResponse
    const select = etc.select || null

    if (!bodyContains(elt)) {

      maybeCall(resolve)
      return promise
    }
    const target = etc.targetOverride || asElement(getTarget(elt))
    if (target == null || target == DUMMY_ELT) {
      triggerErrorEvent(elt, 'htmx:targetError', { target: getAttributeValue(elt, 'hx-target') })
      maybeCall(reject)
      return promise
    }

    let eltData = getInternalData(elt)
    const submitter = eltData.lastButtonClicked

    if (submitter) {
      const buttonPath = getRawAttribute(submitter, 'formaction')
      if (buttonPath != null) {
        path = buttonPath
      }

      const buttonVerb = getRawAttribute(submitter, 'formmethod')
      if (buttonVerb != null) {

        if (buttonVerb.toLowerCase() !== 'dialog') {
          verb = ((buttonVerb))
        }
      }
    }

    const confirmQuestion = getClosestAttributeValue(elt, 'hx-confirm')

    if (confirmed === undefined) {
      const issueRequest = function(skipConfirmation) {
        return issueAjaxRequest(verb, path, elt, event, etc, !!skipConfirmation)
      }
      const confirmDetails = { target, elt, path, verb, triggeringEvent: event, etc, issueRequest, question: confirmQuestion }
      if (triggerEvent(elt, 'htmx:confirm', confirmDetails) === false) {
        maybeCall(resolve)
        return promise
      }
    }

    let syncElt = elt
    let syncStrategy = getClosestAttributeValue(elt, 'hx-sync')
    let queueStrategy = null
    let abortable = false
    if (syncStrategy) {
      const syncStrings = syncStrategy.split(':')
      const selector = syncStrings[0].trim()
      if (selector === 'this') {
        syncElt = findThisElement(elt, 'hx-sync')
      } else {
        syncElt = asElement(querySelectorExt(elt, selector))
      }

      syncStrategy = (syncStrings[1] || 'drop').trim()
      eltData = getInternalData(syncElt)
      if (syncStrategy === 'drop' && eltData.xhr && eltData.abortable !== true) {
        maybeCall(resolve)
        return promise
      } else if (syncStrategy === 'abort') {
        if (eltData.xhr) {
          maybeCall(resolve)
          return promise
        } else {
          abortable = true
        }
      } else if (syncStrategy === 'replace') {
        triggerEvent(syncElt, 'htmx:abort')
      } else if (syncStrategy.indexOf('queue') === 0) {
        const queueStrArray = syncStrategy.split(' ')
        queueStrategy = (queueStrArray[1] || 'last').trim()
      }
    }

    if (eltData.xhr) {
      if (eltData.abortable) {
        triggerEvent(syncElt, 'htmx:abort')
      } else {
        if (queueStrategy == null) {
          if (event) {
            const eventData = getInternalData(event)
            if (eventData && eventData.triggerSpec && eventData.triggerSpec.queue) {
              queueStrategy = eventData.triggerSpec.queue
            }
          }
          if (queueStrategy == null) {
            queueStrategy = 'last'
          }
        }
        if (eltData.queuedRequests == null) {
          eltData.queuedRequests = []
        }
        if (queueStrategy === 'first' && eltData.queuedRequests.length === 0) {
          eltData.queuedRequests.push(function() {
            issueAjaxRequest(verb, path, elt, event, etc)
          })
        } else if (queueStrategy === 'all') {
          eltData.queuedRequests.push(function() {
            issueAjaxRequest(verb, path, elt, event, etc)
          })
        } else if (queueStrategy === 'last') {
          eltData.queuedRequests = []
          eltData.queuedRequests.push(function() {
            issueAjaxRequest(verb, path, elt, event, etc)
          })
        }
        maybeCall(resolve)
        return promise
      }
    }

    const xhr = new XMLHttpRequest()
    eltData.xhr = xhr
    eltData.abortable = abortable
    const endRequestLock = function() {
      eltData.xhr = null
      eltData.abortable = false
      if (eltData.queuedRequests != null &&
      eltData.queuedRequests.length > 0) {
        const queuedRequest = eltData.queuedRequests.shift()
        queuedRequest()
      }
    }
    const promptQuestion = getClosestAttributeValue(elt, 'hx-prompt')
    if (promptQuestion) {
      var promptResponse = prompt(promptQuestion)

      if (promptResponse === null ||
      !triggerEvent(elt, 'htmx:prompt', { prompt: promptResponse, target })) {
        maybeCall(resolve)
        endRequestLock()
        return promise
      }
    }

    if (confirmQuestion && !confirmed) {
      if (!confirm(confirmQuestion)) {
        maybeCall(resolve)
        endRequestLock()
        return promise
      }
    }

    let headers = getHeaders(elt, target, promptResponse)

    if (verb !== 'get' && !usesFormData(elt)) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
    }

    if (etc.headers) {
      headers = mergeObjects(headers, etc.headers)
    }
    const results = getInputValues(elt, verb)
    let errors = results.errors
    const rawFormData = results.formData
    if (etc.values) {
      overrideFormData(rawFormData, formDataFromObject(etc.values))
    }
    const expressionVars = formDataFromObject(getExpressionVars(elt))
    const allFormData = overrideFormData(rawFormData, expressionVars)
    let filteredFormData = filterValues(allFormData, elt)

    if (htmx.config.getCacheBusterParam && verb === 'get') {
      filteredFormData.set('org.htmx.cache-buster', getRawAttribute(target, 'id') || 'true')
    }


    if (path == null || path === '') {
      path = getDocument().location.href
    }


    const requestAttrValues = getValuesForElement(elt, 'hx-request')

    const eltIsBoosted = getInternalData(elt).boosted

    let useUrlParams = htmx.config.methodsThatUseUrlParams.indexOf(verb) >= 0


    const requestConfig = {
      boosted: eltIsBoosted,
      useUrlParams,
      formData: filteredFormData,
      parameters: formDataProxy(filteredFormData),
      unfilteredFormData: allFormData,
      unfilteredParameters: formDataProxy(allFormData),
      headers,
      target,
      verb,
      errors,
      withCredentials: etc.credentials || requestAttrValues.credentials || htmx.config.withCredentials,
      timeout: etc.timeout || requestAttrValues.timeout || htmx.config.timeout,
      path,
      triggeringEvent: event
    }

    if (!triggerEvent(elt, 'htmx:configRequest', requestConfig)) {
      maybeCall(resolve)
      endRequestLock()
      return promise
    }


    path = requestConfig.path
    verb = requestConfig.verb
    headers = requestConfig.headers
    filteredFormData = formDataFromObject(requestConfig.parameters)
    errors = requestConfig.errors
    useUrlParams = requestConfig.useUrlParams

    if (errors && errors.length > 0) {
      triggerEvent(elt, 'htmx:validation:halted', requestConfig)
      maybeCall(resolve)
      endRequestLock()
      return promise
    }

    const splitPath = path.split('#')
    const pathNoAnchor = splitPath[0]
    const anchor = splitPath[1]

    let finalPath = path
    if (useUrlParams) {
      finalPath = pathNoAnchor
      const hasValues = !filteredFormData.keys().next().done
      if (hasValues) {
        if (finalPath.indexOf('?') < 0) {
          finalPath += '?'
        } else {
          finalPath += '&'
        }
        finalPath += urlEncode(filteredFormData)
        if (anchor) {
          finalPath += '#' + anchor
        }
      }
    }

    if (!verifyPath(elt, finalPath, requestConfig)) {
      triggerErrorEvent(elt, 'htmx:invalidPath', requestConfig)
      maybeCall(reject)
      return promise
    }

    xhr.open(verb.toUpperCase(), finalPath, true)
    xhr.overrideMimeType('text/html')
    xhr.withCredentials = requestConfig.withCredentials
    xhr.timeout = requestConfig.timeout


    if (requestAttrValues.noHeaders) {

    } else {
      for (const header in headers) {
        if (headers.hasOwnProperty(header)) {
          const headerValue = headers[header]
          safelySetHeaderValue(xhr, header, headerValue)
        }
      }
    }


    const responseInfo = {
      xhr,
      target,
      requestConfig,
      etc,
      boosted: eltIsBoosted,
      select,
      pathInfo: {
        requestPath: path,
        finalRequestPath: finalPath,
        responsePath: null,
        anchor
      }
    }

    xhr.onload = function() {
      try {
        const hierarchy = hierarchyForElt(elt)
        responseInfo.pathInfo.responsePath = getPathFromResponse(xhr)
        responseHandler(elt, responseInfo)
        if (responseInfo.keepIndicators !== true) {
          removeRequestIndicators(indicators, disableElts)
        }
        triggerEvent(elt, 'htmx:afterRequest', responseInfo)
        triggerEvent(elt, 'htmx:afterOnLoad', responseInfo)


        if (!bodyContains(elt)) {
          let secondaryTriggerElt = null
          while (hierarchy.length > 0 && secondaryTriggerElt == null) {
            const parentEltInHierarchy = hierarchy.shift()
            if (bodyContains(parentEltInHierarchy)) {
              secondaryTriggerElt = parentEltInHierarchy
            }
          }
          if (secondaryTriggerElt) {
            triggerEvent(secondaryTriggerElt, 'htmx:afterRequest', responseInfo)
            triggerEvent(secondaryTriggerElt, 'htmx:afterOnLoad', responseInfo)
          }
        }
        maybeCall(resolve)
        endRequestLock()
      } catch (e) {
        triggerErrorEvent(elt, 'htmx:onLoadError', mergeObjects({ error: e }, responseInfo))
        throw e
      }
    }
    xhr.onerror = function() {
      removeRequestIndicators(indicators, disableElts)
      triggerErrorEvent(elt, 'htmx:afterRequest', responseInfo)
      triggerErrorEvent(elt, 'htmx:sendError', responseInfo)
      maybeCall(reject)
      endRequestLock()
    }
    xhr.onabort = function() {
      removeRequestIndicators(indicators, disableElts)
      triggerErrorEvent(elt, 'htmx:afterRequest', responseInfo)
      triggerErrorEvent(elt, 'htmx:sendAbort', responseInfo)
      maybeCall(reject)
      endRequestLock()
    }
    xhr.ontimeout = function() {
      removeRequestIndicators(indicators, disableElts)
      triggerErrorEvent(elt, 'htmx:afterRequest', responseInfo)
      triggerErrorEvent(elt, 'htmx:timeout', responseInfo)
      maybeCall(reject)
      endRequestLock()
    }
    if (!triggerEvent(elt, 'htmx:beforeRequest', responseInfo)) {
      maybeCall(resolve)
      endRequestLock()
      return promise
    }
    var indicators = addRequestIndicatorClasses(elt)
    var disableElts = disableElements(elt)

    forEach(['loadstart', 'loadend', 'progress', 'abort'], function(eventName) {
      forEach([xhr, xhr.upload], function(target) {
        target.addEventListener(eventName, function(event) {
          triggerEvent(elt, 'htmx:xhr:' + eventName, {
            lengthComputable: event.lengthComputable,
            loaded: event.loaded,
            total: event.total
          })
        })
      })
    })
    triggerEvent(elt, 'htmx:beforeSend', responseInfo)
    const params = useUrlParams ? null : encodeParamsForBody(xhr, elt, filteredFormData)
    xhr.send(params)
    return promise
  }




  function determineHistoryUpdates(elt, responseInfo) {
    const xhr = responseInfo.xhr




    let pathFromHeaders = null
    let typeFromHeaders = null
    if (hasHeader(xhr, /HX-Push:/i)) {
      pathFromHeaders = xhr.getResponseHeader('HX-Push')
      typeFromHeaders = 'push'
    } else if (hasHeader(xhr, /HX-Push-Url:/i)) {
      pathFromHeaders = xhr.getResponseHeader('HX-Push-Url')
      typeFromHeaders = 'push'
    } else if (hasHeader(xhr, /HX-Replace-Url:/i)) {
      pathFromHeaders = xhr.getResponseHeader('HX-Replace-Url')
      typeFromHeaders = 'replace'
    }


    if (pathFromHeaders) {
      if (pathFromHeaders === 'false') {
        return {}
      } else {
        return {
          type: typeFromHeaders,
          path: pathFromHeaders
        }
      }
    }




    const requestPath = responseInfo.pathInfo.finalRequestPath
    const responsePath = responseInfo.pathInfo.responsePath

    const pushUrl = getClosestAttributeValue(elt, 'hx-push-url')
    const replaceUrl = getClosestAttributeValue(elt, 'hx-replace-url')
    const elementIsBoosted = getInternalData(elt).boosted

    let saveType = null
    let path = null

    if (pushUrl) {
      saveType = 'push'
      path = pushUrl
    } else if (replaceUrl) {
      saveType = 'replace'
      path = replaceUrl
    } else if (elementIsBoosted) {
      saveType = 'push'
      path = responsePath || requestPath
    }

    if (path) {

      if (path === 'false') {
        return {}
      }


      if (path === 'true') {
        path = responsePath || requestPath
      }


      if (responseInfo.pathInfo.anchor && path.indexOf('#') === -1) {
        path = path + '#' + responseInfo.pathInfo.anchor
      }

      return {
        type: saveType,
        path
      }
    } else {
      return {}
    }
  }


  function codeMatches(responseHandlingConfig, status) {
    var regExp = new RegExp(responseHandlingConfig.code)
    return regExp.test(status.toString(10))
  }


  function resolveResponseHandling(xhr) {
    for (var i = 0; i < htmx.config.responseHandling.length; i++) {

      var responseHandlingElement = htmx.config.responseHandling[i]
      if (codeMatches(responseHandlingElement, xhr.status)) {
        return responseHandlingElement
      }
    }

    return {
      swap: false
    }
  }


  function handleTitle(title) {
    if (title) {
      const titleElt = find('title')
      if (titleElt) {
        titleElt.innerHTML = title
      } else {
        window.document.title = title
      }
    }
  }


  function handleAjaxResponse(elt, responseInfo) {
    const xhr = responseInfo.xhr
    let target = responseInfo.target
    const etc = responseInfo.etc
    const responseInfoSelect = responseInfo.select

    if (!triggerEvent(elt, 'htmx:beforeOnLoad', responseInfo)) return

    if (hasHeader(xhr, /HX-Trigger:/i)) {
      handleTriggerHeader(xhr, 'HX-Trigger', elt)
    }

    if (hasHeader(xhr, /HX-Location:/i)) {
      saveCurrentPageToHistory()
      let redirectPath = xhr.getResponseHeader('HX-Location')

      var redirectSwapSpec
      if (redirectPath.indexOf('{') === 0) {
        redirectSwapSpec = parseJSON(redirectPath)

        redirectPath = redirectSwapSpec.path
        delete redirectSwapSpec.path
      }
      ajaxHelper('get', redirectPath, redirectSwapSpec).then(function() {
        pushUrlIntoHistory(redirectPath)
      })
      return
    }

    const shouldRefresh = hasHeader(xhr, /HX-Refresh:/i) && xhr.getResponseHeader('HX-Refresh') === 'true'

    if (hasHeader(xhr, /HX-Redirect:/i)) {
      responseInfo.keepIndicators = true
      location.href = xhr.getResponseHeader('HX-Redirect')
      shouldRefresh && location.reload()
      return
    }

    if (shouldRefresh) {
      responseInfo.keepIndicators = true
      location.reload()
      return
    }

    if (hasHeader(xhr, /HX-Retarget:/i)) {
      if (xhr.getResponseHeader('HX-Retarget') === 'this') {
        responseInfo.target = elt
      } else {
        responseInfo.target = asElement(querySelectorExt(elt, xhr.getResponseHeader('HX-Retarget')))
      }
    }

    const historyUpdate = determineHistoryUpdates(elt, responseInfo)

    const responseHandling = resolveResponseHandling(xhr)
    const shouldSwap = responseHandling.swap
    let isError = !!responseHandling.error
    let ignoreTitle = htmx.config.ignoreTitle || responseHandling.ignoreTitle
    let selectOverride = responseHandling.select
    if (responseHandling.target) {
      responseInfo.target = asElement(querySelectorExt(elt, responseHandling.target))
    }
    var swapOverride = etc.swapOverride
    if (swapOverride == null && responseHandling.swapOverride) {
      swapOverride = responseHandling.swapOverride
    }


    if (hasHeader(xhr, /HX-Retarget:/i)) {
      if (xhr.getResponseHeader('HX-Retarget') === 'this') {
        responseInfo.target = elt
      } else {
        responseInfo.target = asElement(querySelectorExt(elt, xhr.getResponseHeader('HX-Retarget')))
      }
    }
    if (hasHeader(xhr, /HX-Reswap:/i)) {
      swapOverride = xhr.getResponseHeader('HX-Reswap')
    }

    var serverResponse = xhr.response

    var beforeSwapDetails = mergeObjects({
      shouldSwap,
      serverResponse,
      isError,
      ignoreTitle,
      selectOverride,
      swapOverride
    }, responseInfo)

    if (responseHandling.event && !triggerEvent(target, responseHandling.event, beforeSwapDetails)) return

    if (!triggerEvent(target, 'htmx:beforeSwap', beforeSwapDetails)) return

    target = beforeSwapDetails.target
    serverResponse = beforeSwapDetails.serverResponse
    isError = beforeSwapDetails.isError
    ignoreTitle = beforeSwapDetails.ignoreTitle
    selectOverride = beforeSwapDetails.selectOverride
    swapOverride = beforeSwapDetails.swapOverride

    responseInfo.target = target
    responseInfo.failed = isError
    responseInfo.successful = !isError

    if (beforeSwapDetails.shouldSwap) {
      if (xhr.status === 286) {
        cancelPolling(elt)
      }

      withExtensions(elt, function(extension) {
        serverResponse = extension.transformResponse(serverResponse, xhr, elt)
      })


      if (historyUpdate.type) {
        saveCurrentPageToHistory()
      }

      var swapSpec = getSwapSpecification(elt, swapOverride)

      if (!swapSpec.hasOwnProperty('ignoreTitle')) {
        swapSpec.ignoreTitle = ignoreTitle
      }

      target.classList.add(htmx.config.swappingClass)


      let settleResolve = null
      let settleReject = null

      if (responseInfoSelect) {
        selectOverride = responseInfoSelect
      }

      if (hasHeader(xhr, /HX-Reselect:/i)) {
        selectOverride = xhr.getResponseHeader('HX-Reselect')
      }

      const selectOOB = getClosestAttributeValue(elt, 'hx-select-oob')
      const select = getClosestAttributeValue(elt, 'hx-select')

      let doSwap = function() {
        try {

          if (historyUpdate.type) {
            triggerEvent(getDocument().body, 'htmx:beforeHistoryUpdate', mergeObjects({ history: historyUpdate }, responseInfo))
            if (historyUpdate.type === 'push') {
              pushUrlIntoHistory(historyUpdate.path)
              triggerEvent(getDocument().body, 'htmx:pushedIntoHistory', { path: historyUpdate.path })
            } else {
              replaceUrlInHistory(historyUpdate.path)
              triggerEvent(getDocument().body, 'htmx:replacedInHistory', { path: historyUpdate.path })
            }
          }

          swap(target, serverResponse, swapSpec, {
            select: selectOverride || select,
            selectOOB,
            eventInfo: responseInfo,
            anchor: responseInfo.pathInfo.anchor,
            contextElement: elt,
            afterSwapCallback: function() {
              if (hasHeader(xhr, /HX-Trigger-After-Swap:/i)) {
                let finalElt = elt
                if (!bodyContains(elt)) {
                  finalElt = getDocument().body
                }
                handleTriggerHeader(xhr, 'HX-Trigger-After-Swap', finalElt)
              }
            },
            afterSettleCallback: function() {
              if (hasHeader(xhr, /HX-Trigger-After-Settle:/i)) {
                let finalElt = elt
                if (!bodyContains(elt)) {
                  finalElt = getDocument().body
                }
                handleTriggerHeader(xhr, 'HX-Trigger-After-Settle', finalElt)
              }
              maybeCall(settleResolve)
            }
          })
        } catch (e) {
          triggerErrorEvent(elt, 'htmx:swapError', responseInfo)
          maybeCall(settleReject)
          throw e
        }
      }

      let shouldTransition = htmx.config.globalViewTransitions
      if (swapSpec.hasOwnProperty('transition')) {
        shouldTransition = swapSpec.transition
      }

      if (shouldTransition &&
              triggerEvent(elt, 'htmx:beforeTransition', responseInfo) &&
              typeof Promise !== 'undefined' &&

              document.startViewTransition) {
        const settlePromise = new Promise(function(_resolve, _reject) {
          settleResolve = _resolve
          settleReject = _reject
        })

        const innerDoSwap = doSwap
        doSwap = function() {

          document.startViewTransition(function() {
            innerDoSwap()
            return settlePromise
          })
        }
      }

      if (swapSpec.swapDelay > 0) {
        getWindow().setTimeout(doSwap, swapSpec.swapDelay)
      } else {
        doSwap()
      }
    }
    if (isError) {
      triggerErrorEvent(elt, 'htmx:responseError', mergeObjects({ error: 'Response Status Error Code ' + xhr.status + ' from ' + responseInfo.pathInfo.requestPath }, responseInfo))
    }
  }






  const extensions = {}


  function extensionBase() {
    return {
      init: function(api) { return null },
      getSelectors: function() { return null },
      onEvent: function(name, evt) { return true },
      transformResponse: function(text, xhr, elt) { return text },
      isInlineSwap: function(swapStyle) { return false },
      handleSwap: function(swapStyle, target, fragment, settleInfo) { return false },
      encodeParameters: function(xhr, parameters, elt) { return null }
    }
  }


  function defineExtension(name, extension) {
    if (extension.init) {
      extension.init(internalAPI)
    }
    extensions[name] = mergeObjects(extensionBase(), extension)
  }


  function removeExtension(name) {
    delete extensions[name]
  }


  function getExtensions(elt, extensionsToReturn, extensionsToIgnore) {
    if (extensionsToReturn == undefined) {
      extensionsToReturn = []
    }
    if (elt == undefined) {
      return extensionsToReturn
    }
    if (extensionsToIgnore == undefined) {
      extensionsToIgnore = []
    }
    const extensionsForElement = getAttributeValue(elt, 'hx-ext')
    if (extensionsForElement) {
      forEach(extensionsForElement.split(','), function(extensionName) {
        extensionName = extensionName.replace(/ /g, '')
        if (extensionName.slice(0, 7) == 'ignore:') {
          extensionsToIgnore.push(extensionName.slice(7))
          return
        }
        if (extensionsToIgnore.indexOf(extensionName) < 0) {
          const extension = extensions[extensionName]
          if (extension && extensionsToReturn.indexOf(extension) < 0) {
            extensionsToReturn.push(extension)
          }
        }
      })
    }
    return getExtensions(asElement(parentElt(elt)), extensionsToReturn, extensionsToIgnore)
  }




  var isReady = false
  getDocument().addEventListener('DOMContentLoaded', function() {
    isReady = true
  })


  function ready(fn) {


    if (isReady || getDocument().readyState === 'complete') {
      fn()
    } else {
      getDocument().addEventListener('DOMContentLoaded', fn)
    }
  }

  function insertIndicatorStyles() {
    if (htmx.config.includeIndicatorStyles !== false) {
      const nonceAttribute = htmx.config.inlineStyleNonce ? ` nonce="${htmx.config.inlineStyleNonce}"` : ''
      getDocument().head.insertAdjacentHTML('beforeend',
        '<style' + nonceAttribute + '>\
      .' + htmx.config.indicatorClass + '{opacity:0}\
      .' + htmx.config.requestClass + ' .' + htmx.config.indicatorClass + '{opacity:1; transition: opacity 200ms ease-in;}\
      .' + htmx.config.requestClass + '.' + htmx.config.indicatorClass + '{opacity:1; transition: opacity 200ms ease-in;}\
      </style>')
    }
  }

  function getMetaConfig() {

    const element = getDocument().querySelector('meta[name="htmx-config"]')
    if (element) {
      return parseJSON(element.content)
    } else {
      return null
    }
  }

  function mergeMetaConfig() {
    const metaConfig = getMetaConfig()
    if (metaConfig) {
      htmx.config = mergeObjects(htmx.config, metaConfig)
    }
  }


  ready(function() {
    mergeMetaConfig()
    insertIndicatorStyles()
    let body = getDocument().body
    processNode(body)
    const restoredElts = getDocument().querySelectorAll(
      "[hx-trigger='restored'],[data-hx-trigger='restored']"
    )
    body.addEventListener('htmx:abort', function(evt) {
      const target = evt.target
      const internalData = getInternalData(target)
      if (internalData && internalData.xhr) {
        internalData.xhr.abort()
      }
    })

    const originalPopstate = window.onpopstate ? window.onpopstate.bind(window) : null

    window.onpopstate = function(event) {
      if (event.state && event.state.htmx) {
        restoreHistory()
        forEach(restoredElts, function(elt) {
          triggerEvent(elt, 'htmx:restored', {
            document: getDocument(),
            triggerEvent
          })
        })
      } else {
        if (originalPopstate) {
          originalPopstate(event)
        }
      }
    }
    getWindow().setTimeout(function() {
      triggerEvent(body, 'htmx:load', {})
      body = null
    }, 0)
  })

  return htmx
})()






































;





(function() {

  var api

  htmx.defineExtension('ws', {


    init: function(apiRef) {

      api = apiRef


      if (!htmx.createWebSocket) {
        htmx.createWebSocket = createWebSocket
      }


      if (!htmx.config.wsReconnectDelay) {
        htmx.config.wsReconnectDelay = 'full-jitter'
      }
    },


    onEvent: function(name, evt) {
      var parent = evt.target || evt.detail.elt
      switch (name) {

        case 'htmx:beforeCleanupElement':

          var internalData = api.getInternalData(parent)

          if (internalData.webSocket) {
            internalData.webSocket.close()
          }
          return


        case 'htmx:beforeProcessNode':

          forEach(queryAttributeOnThisOrChildren(parent, 'ws-connect'), function(child) {
            ensureWebSocket(child)
          })
          forEach(queryAttributeOnThisOrChildren(parent, 'ws-send'), function(child) {
            ensureWebSocketSend(child)
          })
      }
    }
  })

  function splitOnWhitespace(trigger) {
    return trigger.trim().split(/\s+/)
  }

  function getLegacyWebsocketURL(elt) {
    var legacySSEValue = api.getAttributeValue(elt, 'hx-ws')
    if (legacySSEValue) {
      var values = splitOnWhitespace(legacySSEValue)
      for (var i = 0; i < values.length; i++) {
        var value = values[i].split(/:(.+)/)
        if (value[0] === 'connect') {
          return value[1]
        }
      }
    }
  }


  function ensureWebSocket(socketElt) {


    if (!api.bodyContains(socketElt)) {
      return
    }


    var wssSource = api.getAttributeValue(socketElt, 'ws-connect')

    if (wssSource == null || wssSource === '') {
      var legacySource = getLegacyWebsocketURL(socketElt)
      if (legacySource == null) {
        return
      } else {
        wssSource = legacySource
      }
    }


    if (wssSource.indexOf('/') === 0) {
      var base_part = location.hostname + (location.port ? ':' + location.port : '')
      if (location.protocol === 'https:') {
        wssSource = 'wss://' + base_part + wssSource
      } else if (location.protocol === 'http:') {
        wssSource = 'ws://' + base_part + wssSource
      }
    }

    var socketWrapper = createWebsocketWrapper(socketElt, function() {
      return htmx.createWebSocket(wssSource)
    })

    socketWrapper.addEventListener('message', function(event) {
      if (maybeCloseWebSocketSource(socketElt)) {
        return
      }

      var response = event.data
      if (!api.triggerEvent(socketElt, 'htmx:wsBeforeMessage', {
        message: response,
        socketWrapper: socketWrapper.publicInterface
      })) {
        return
      }

      api.withExtensions(socketElt, function(extension) {
        response = extension.transformResponse(response, null, socketElt)
      })

      var settleInfo = api.makeSettleInfo(socketElt)
      var fragment = api.makeFragment(response)

      if (fragment.children.length) {
        var children = Array.from(fragment.children)
        for (var i = 0; i < children.length; i++) {
          api.oobSwap(api.getAttributeValue(children[i], 'hx-swap-oob') || 'true', children[i], settleInfo)
        }
      }

      api.settleImmediately(settleInfo.tasks)
      api.triggerEvent(socketElt, 'htmx:wsAfterMessage', { message: response, socketWrapper: socketWrapper.publicInterface })
    })


    api.getInternalData(socketElt).webSocket = socketWrapper
  }



  function createWebsocketWrapper(socketElt, socketFunc) {
    var wrapper = {
      socket: null,
      messageQueue: [],
      retryCount: 0,


      events: {},

      addEventListener: function(event, handler) {
        if (this.socket) {
          this.socket.addEventListener(event, handler)
        }

        if (!this.events[event]) {
          this.events[event] = []
        }

        this.events[event].push(handler)
      },

      sendImmediately: function(message, sendElt) {
        if (!this.socket) {
          api.triggerErrorEvent()
        }
        if (!sendElt || api.triggerEvent(sendElt, 'htmx:wsBeforeSend', {
          message,
          socketWrapper: this.publicInterface
        })) {
          this.socket.send(message)
          sendElt && api.triggerEvent(sendElt, 'htmx:wsAfterSend', {
            message,
            socketWrapper: this.publicInterface
          })
        }
      },

      send: function(message, sendElt) {
        if (this.socket.readyState !== this.socket.OPEN) {
          this.messageQueue.push({ message, sendElt })
        } else {
          this.sendImmediately(message, sendElt)
        }
      },

      handleQueuedMessages: function() {
        while (this.messageQueue.length > 0) {
          var queuedItem = this.messageQueue[0]
          if (this.socket.readyState === this.socket.OPEN) {
            this.sendImmediately(queuedItem.message, queuedItem.sendElt)
            this.messageQueue.shift()
          } else {
            break
          }
        }
      },

      init: function() {
        if (this.socket && this.socket.readyState === this.socket.OPEN) {

          this.socket.close()
        }



        var socket = socketFunc()




        api.triggerEvent(socketElt, 'htmx:wsConnecting', { event: { type: 'connecting' } })

        this.socket = socket

        socket.onopen = function(e) {
          wrapper.retryCount = 0
          api.triggerEvent(socketElt, 'htmx:wsOpen', { event: e, socketWrapper: wrapper.publicInterface })
          wrapper.handleQueuedMessages()
        }

        socket.onclose = function(e) {


          if (!maybeCloseWebSocketSource(socketElt) && [1006, 1012, 1013].indexOf(e.code) >= 0) {
            var delay = getWebSocketReconnectDelay(wrapper.retryCount)
            setTimeout(function() {
              wrapper.retryCount += 1
              wrapper.init()
            }, delay)
          }



          api.triggerEvent(socketElt, 'htmx:wsClose', { event: e, socketWrapper: wrapper.publicInterface })
        }

        socket.onerror = function(e) {
          api.triggerErrorEvent(socketElt, 'htmx:wsError', { error: e, socketWrapper: wrapper })
          maybeCloseWebSocketSource(socketElt)
        }

        var events = this.events
        Object.keys(events).forEach(function(k) {
          events[k].forEach(function(e) {
            socket.addEventListener(k, e)
          })
        })
      },

      close: function() {
        this.socket.close()
      }
    }

    wrapper.init()

    wrapper.publicInterface = {
      send: wrapper.send.bind(wrapper),
      sendImmediately: wrapper.sendImmediately.bind(wrapper),
      queue: wrapper.messageQueue
    }

    return wrapper
  }


  function ensureWebSocketSend(elt) {
    var legacyAttribute = api.getAttributeValue(elt, 'hx-ws')
    if (legacyAttribute && legacyAttribute !== 'send') {
      return
    }

    var webSocketParent = api.getClosestMatch(elt, hasWebSocket)
    processWebSocketSend(webSocketParent, elt)
  }


  function hasWebSocket(node) {
    return api.getInternalData(node).webSocket != null
  }


  function processWebSocketSend(socketElt, sendElt) {
    var nodeData = api.getInternalData(sendElt)
    var triggerSpecs = api.getTriggerSpecs(sendElt)
    triggerSpecs.forEach(function(ts) {
      api.addTriggerHandler(sendElt, ts, nodeData, function(elt, evt) {
        if (maybeCloseWebSocketSource(socketElt)) {
          return
        }


        var socketWrapper = api.getInternalData(socketElt).webSocket
        var headers = api.getHeaders(sendElt, api.getTarget(sendElt))
        var results = api.getInputValues(sendElt, 'post')
        var errors = results.errors
        var rawParameters = Object.assign({}, results.values)
        var expressionVars = api.getExpressionVars(sendElt)
        var allParameters = api.mergeObjects(rawParameters, expressionVars)
        var filteredParameters = api.filterValues(allParameters, sendElt)

        var sendConfig = {
          parameters: filteredParameters,
          unfilteredParameters: allParameters,
          headers,
          errors,

          triggeringEvent: evt,
          messageBody: undefined,
          socketWrapper: socketWrapper.publicInterface
        }

        if (!api.triggerEvent(elt, 'htmx:wsConfigSend', sendConfig)) {
          return
        }

        if (errors && errors.length > 0) {
          api.triggerEvent(elt, 'htmx:validation:halted', errors)
          return
        }

        var body = sendConfig.messageBody
        if (body === undefined) {
          var toSend = Object.assign({}, sendConfig.parameters)
          if (sendConfig.headers) { toSend.HEADERS = headers }
          body = JSON.stringify(toSend)
        }

        socketWrapper.send(body, elt)

        if (evt && api.shouldCancel(evt, elt)) {
          evt.preventDefault()
        }
      })
    })
  }


  function getWebSocketReconnectDelay(retryCount) {

    var delay = htmx.config.wsReconnectDelay
    if (typeof delay === 'function') {
      return delay(retryCount)
    }
    if (delay === 'full-jitter') {
      var exp = Math.min(retryCount, 6)
      var maxDelay = 1000 * Math.pow(2, exp)
      return maxDelay * Math.random()
    }

    logError('htmx.config.wsReconnectDelay must either be a function or the string "full-jitter"')
  }


  function maybeCloseWebSocketSource(elt) {
    if (!api.bodyContains(elt)) {
      api.getInternalData(elt).webSocket.close()
      return true
    }
    return false
  }


  function createWebSocket(url) {
    var sock = new WebSocket(url, [])
    sock.binaryType = htmx.config.wsBinaryType
    return sock
  }


  function queryAttributeOnThisOrChildren(elt, attributeName) {
    var result = []


    if (api.hasAttribute(elt, attributeName) || api.hasAttribute(elt, 'hx-ws')) {
      result.push(elt)
    }


    elt.querySelectorAll('[' + attributeName + '], [data-' + attributeName + '], [data-hx-ws], [hx-ws]').forEach(function(node) {
      result.push(node)
    })

    return result
  }


  function forEach(arr, func) {
    if (arr) {
      for (var i = 0; i < arr.length; i++) {
        func(arr[i])
      }
    }
  }
})()
;




(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
  typeof define === 'function' && define.amd ? define(factory) :
  (global = global || self, global.Sortable = factory());
}(this, (function () { 'use strict';

  function ownKeys(object, enumerableOnly) {
    var keys = Object.keys(object);
    if (Object.getOwnPropertySymbols) {
      var symbols = Object.getOwnPropertySymbols(object);
      if (enumerableOnly) {
        symbols = symbols.filter(function (sym) {
          return Object.getOwnPropertyDescriptor(object, sym).enumerable;
        });
      }
      keys.push.apply(keys, symbols);
    }
    return keys;
  }
  function _objectSpread2(target) {
    for (var i = 1; i < arguments.length; i++) {
      var source = arguments[i] != null ? arguments[i] : {};
      if (i % 2) {
        ownKeys(Object(source), true).forEach(function (key) {
          _defineProperty(target, key, source[key]);
        });
      } else if (Object.getOwnPropertyDescriptors) {
        Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
      } else {
        ownKeys(Object(source)).forEach(function (key) {
          Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
        });
      }
    }
    return target;
  }
  function _typeof(obj) {
    "@babel/helpers - typeof";

    if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") {
      _typeof = function (obj) {
        return typeof obj;
      };
    } else {
      _typeof = function (obj) {
        return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj;
      };
    }
    return _typeof(obj);
  }
  function _defineProperty(obj, key, value) {
    if (key in obj) {
      Object.defineProperty(obj, key, {
        value: value,
        enumerable: true,
        configurable: true,
        writable: true
      });
    } else {
      obj[key] = value;
    }
    return obj;
  }
  function _extends() {
    _extends = Object.assign || function (target) {
      for (var i = 1; i < arguments.length; i++) {
        var source = arguments[i];
        for (var key in source) {
          if (Object.prototype.hasOwnProperty.call(source, key)) {
            target[key] = source[key];
          }
        }
      }
      return target;
    };
    return _extends.apply(this, arguments);
  }
  function _objectWithoutPropertiesLoose(source, excluded) {
    if (source == null) return {};
    var target = {};
    var sourceKeys = Object.keys(source);
    var key, i;
    for (i = 0; i < sourceKeys.length; i++) {
      key = sourceKeys[i];
      if (excluded.indexOf(key) >= 0) continue;
      target[key] = source[key];
    }
    return target;
  }
  function _objectWithoutProperties(source, excluded) {
    if (source == null) return {};
    var target = _objectWithoutPropertiesLoose(source, excluded);
    var key, i;
    if (Object.getOwnPropertySymbols) {
      var sourceSymbolKeys = Object.getOwnPropertySymbols(source);
      for (i = 0; i < sourceSymbolKeys.length; i++) {
        key = sourceSymbolKeys[i];
        if (excluded.indexOf(key) >= 0) continue;
        if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue;
        target[key] = source[key];
      }
    }
    return target;
  }
  function _toConsumableArray(arr) {
    return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread();
  }
  function _arrayWithoutHoles(arr) {
    if (Array.isArray(arr)) return _arrayLikeToArray(arr);
  }
  function _iterableToArray(iter) {
    if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null) return Array.from(iter);
  }
  function _unsupportedIterableToArray(o, minLen) {
    if (!o) return;
    if (typeof o === "string") return _arrayLikeToArray(o, minLen);
    var n = Object.prototype.toString.call(o).slice(8, -1);
    if (n === "Object" && o.constructor) n = o.constructor.name;
    if (n === "Map" || n === "Set") return Array.from(o);
    if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen);
  }
  function _arrayLikeToArray(arr, len) {
    if (len == null || len > arr.length) len = arr.length;
    for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i];
    return arr2;
  }
  function _nonIterableSpread() {
    throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
  }

  var version = "1.15.2";

  function userAgent(pattern) {
    if (typeof window !== 'undefined' && window.navigator) {
      return !! navigator.userAgent.match(pattern);
    }
  }
  var IE11OrLess = userAgent(/(?:Trident.*rv[ :]?11\.|msie|iemobile|Windows Phone)/i);
  var Edge = userAgent(/Edge/i);
  var FireFox = userAgent(/firefox/i);
  var Safari = userAgent(/safari/i) && !userAgent(/chrome/i) && !userAgent(/android/i);
  var IOS = userAgent(/iP(ad|od|hone)/i);
  var ChromeForAndroid = userAgent(/chrome/i) && userAgent(/android/i);

  var captureMode = {
    capture: false,
    passive: false
  };
  function on(el, event, fn) {
    el.addEventListener(event, fn, !IE11OrLess && captureMode);
  }
  function off(el, event, fn) {
    el.removeEventListener(event, fn, !IE11OrLess && captureMode);
  }
  function matches( el, selector) {
    if (!selector) return;
    selector[0] === '>' && (selector = selector.substring(1));
    if (el) {
      try {
        if (el.matches) {
          return el.matches(selector);
        } else if (el.msMatchesSelector) {
          return el.msMatchesSelector(selector);
        } else if (el.webkitMatchesSelector) {
          return el.webkitMatchesSelector(selector);
        }
      } catch (_) {
        return false;
      }
    }
    return false;
  }
  function getParentOrHost(el) {
    return el.host && el !== document && el.host.nodeType ? el.host : el.parentNode;
  }
  function closest( el, selector, ctx, includeCTX) {
    if (el) {
      ctx = ctx || document;
      do {
        if (selector != null && (selector[0] === '>' ? el.parentNode === ctx && matches(el, selector) : matches(el, selector)) || includeCTX && el === ctx) {
          return el;
        }
        if (el === ctx) break;

      } while (el = getParentOrHost(el));
    }
    return null;
  }
  var R_SPACE = /\s+/g;
  function toggleClass(el, name, state) {
    if (el && name) {
      if (el.classList) {
        el.classList[state ? 'add' : 'remove'](name);
      } else {
        var className = (' ' + el.className + ' ').replace(R_SPACE, ' ').replace(' ' + name + ' ', ' ');
        el.className = (className + (state ? ' ' + name : '')).replace(R_SPACE, ' ');
      }
    }
  }
  function css(el, prop, val) {
    var style = el && el.style;
    if (style) {
      if (val === void 0) {
        if (document.defaultView && document.defaultView.getComputedStyle) {
          val = document.defaultView.getComputedStyle(el, '');
        } else if (el.currentStyle) {
          val = el.currentStyle;
        }
        return prop === void 0 ? val : val[prop];
      } else {
        if (!(prop in style) && prop.indexOf('webkit') === -1) {
          prop = '-webkit-' + prop;
        }
        style[prop] = val + (typeof val === 'string' ? '' : 'px');
      }
    }
  }
  function matrix(el, selfOnly) {
    var appliedTransforms = '';
    if (typeof el === 'string') {
      appliedTransforms = el;
    } else {
      do {
        var transform = css(el, 'transform');
        if (transform && transform !== 'none') {
          appliedTransforms = transform + ' ' + appliedTransforms;
        }

      } while (!selfOnly && (el = el.parentNode));
    }
    var matrixFn = window.DOMMatrix || window.WebKitCSSMatrix || window.CSSMatrix || window.MSCSSMatrix;

    return matrixFn && new matrixFn(appliedTransforms);
  }
  function find(ctx, tagName, iterator) {
    if (ctx) {
      var list = ctx.getElementsByTagName(tagName),
        i = 0,
        n = list.length;
      if (iterator) {
        for (; i < n; i++) {
          iterator(list[i], i);
        }
      }
      return list;
    }
    return [];
  }
  function getWindowScrollingElement() {
    var scrollingElement = document.scrollingElement;
    if (scrollingElement) {
      return scrollingElement;
    } else {
      return document.documentElement;
    }
  }


  function getRect(el, relativeToContainingBlock, relativeToNonStaticParent, undoScale, container) {
    if (!el.getBoundingClientRect && el !== window) return;
    var elRect, top, left, bottom, right, height, width;
    if (el !== window && el.parentNode && el !== getWindowScrollingElement()) {
      elRect = el.getBoundingClientRect();
      top = elRect.top;
      left = elRect.left;
      bottom = elRect.bottom;
      right = elRect.right;
      height = elRect.height;
      width = elRect.width;
    } else {
      top = 0;
      left = 0;
      bottom = window.innerHeight;
      right = window.innerWidth;
      height = window.innerHeight;
      width = window.innerWidth;
    }
    if ((relativeToContainingBlock || relativeToNonStaticParent) && el !== window) {

      container = container || el.parentNode;



      if (!IE11OrLess) {
        do {
          if (container && container.getBoundingClientRect && (css(container, 'transform') !== 'none' || relativeToNonStaticParent && css(container, 'position') !== 'static')) {
            var containerRect = container.getBoundingClientRect();


            top -= containerRect.top + parseInt(css(container, 'border-top-width'));
            left -= containerRect.left + parseInt(css(container, 'border-left-width'));
            bottom = top + elRect.height;
            right = left + elRect.width;
            break;
          }

        } while (container = container.parentNode);
      }
    }
    if (undoScale && el !== window) {

      var elMatrix = matrix(container || el),
        scaleX = elMatrix && elMatrix.a,
        scaleY = elMatrix && elMatrix.d;
      if (elMatrix) {
        top /= scaleY;
        left /= scaleX;
        width /= scaleX;
        height /= scaleY;
        bottom = top + height;
        right = left + width;
      }
    }
    return {
      top: top,
      left: left,
      bottom: bottom,
      right: right,
      width: width,
      height: height
    };
  }


  function isScrolledPast(el, elSide, parentSide) {
    var parent = getParentAutoScrollElement(el, true),
      elSideVal = getRect(el)[elSide];


    while (parent) {
      var parentSideVal = getRect(parent)[parentSide],
        visible = void 0;
      if (parentSide === 'top' || parentSide === 'left') {
        visible = elSideVal >= parentSideVal;
      } else {
        visible = elSideVal <= parentSideVal;
      }
      if (!visible) return parent;
      if (parent === getWindowScrollingElement()) break;
      parent = getParentAutoScrollElement(parent, false);
    }
    return false;
  }


  function getChild(el, childNum, options, includeDragEl) {
    var currentChild = 0,
      i = 0,
      children = el.children;
    while (i < children.length) {
      if (children[i].style.display !== 'none' && children[i] !== Sortable.ghost && (includeDragEl || children[i] !== Sortable.dragged) && closest(children[i], options.draggable, el, false)) {
        if (currentChild === childNum) {
          return children[i];
        }
        currentChild++;
      }
      i++;
    }
    return null;
  }


  function lastChild(el, selector) {
    var last = el.lastElementChild;
    while (last && (last === Sortable.ghost || css(last, 'display') === 'none' || selector && !matches(last, selector))) {
      last = last.previousElementSibling;
    }
    return last || null;
  }


  function index(el, selector) {
    var index = 0;
    if (!el || !el.parentNode) {
      return -1;
    }


    while (el = el.previousElementSibling) {
      if (el.nodeName.toUpperCase() !== 'TEMPLATE' && el !== Sortable.clone && (!selector || matches(el, selector))) {
        index++;
      }
    }
    return index;
  }


  function getRelativeScrollOffset(el) {
    var offsetLeft = 0,
      offsetTop = 0,
      winScroller = getWindowScrollingElement();
    if (el) {
      do {
        var elMatrix = matrix(el),
          scaleX = elMatrix.a,
          scaleY = elMatrix.d;
        offsetLeft += el.scrollLeft * scaleX;
        offsetTop += el.scrollTop * scaleY;
      } while (el !== winScroller && (el = el.parentNode));
    }
    return [offsetLeft, offsetTop];
  }


  function indexOfObject(arr, obj) {
    for (var i in arr) {
      if (!arr.hasOwnProperty(i)) continue;
      for (var key in obj) {
        if (obj.hasOwnProperty(key) && obj[key] === arr[i][key]) return Number(i);
      }
    }
    return -1;
  }
  function getParentAutoScrollElement(el, includeSelf) {

    if (!el || !el.getBoundingClientRect) return getWindowScrollingElement();
    var elem = el;
    var gotSelf = false;
    do {

      if (elem.clientWidth < elem.scrollWidth || elem.clientHeight < elem.scrollHeight) {
        var elemCSS = css(elem);
        if (elem.clientWidth < elem.scrollWidth && (elemCSS.overflowX == 'auto' || elemCSS.overflowX == 'scroll') || elem.clientHeight < elem.scrollHeight && (elemCSS.overflowY == 'auto' || elemCSS.overflowY == 'scroll')) {
          if (!elem.getBoundingClientRect || elem === document.body) return getWindowScrollingElement();
          if (gotSelf || includeSelf) return elem;
          gotSelf = true;
        }
      }

    } while (elem = elem.parentNode);
    return getWindowScrollingElement();
  }
  function extend(dst, src) {
    if (dst && src) {
      for (var key in src) {
        if (src.hasOwnProperty(key)) {
          dst[key] = src[key];
        }
      }
    }
    return dst;
  }
  function isRectEqual(rect1, rect2) {
    return Math.round(rect1.top) === Math.round(rect2.top) && Math.round(rect1.left) === Math.round(rect2.left) && Math.round(rect1.height) === Math.round(rect2.height) && Math.round(rect1.width) === Math.round(rect2.width);
  }
  var _throttleTimeout;
  function throttle(callback, ms) {
    return function () {
      if (!_throttleTimeout) {
        var args = arguments,
          _this = this;
        if (args.length === 1) {
          callback.call(_this, args[0]);
        } else {
          callback.apply(_this, args);
        }
        _throttleTimeout = setTimeout(function () {
          _throttleTimeout = void 0;
        }, ms);
      }
    };
  }
  function cancelThrottle() {
    clearTimeout(_throttleTimeout);
    _throttleTimeout = void 0;
  }
  function scrollBy(el, x, y) {
    el.scrollLeft += x;
    el.scrollTop += y;
  }
  function clone(el) {
    var Polymer = window.Polymer;
    var $ = window.jQuery || window.Zepto;
    if (Polymer && Polymer.dom) {
      return Polymer.dom(el).cloneNode(true);
    } else if ($) {
      return $(el).clone(true)[0];
    } else {
      return el.cloneNode(true);
    }
  }
  function setRect(el, rect) {
    css(el, 'position', 'absolute');
    css(el, 'top', rect.top);
    css(el, 'left', rect.left);
    css(el, 'width', rect.width);
    css(el, 'height', rect.height);
  }
  function unsetRect(el) {
    css(el, 'position', '');
    css(el, 'top', '');
    css(el, 'left', '');
    css(el, 'width', '');
    css(el, 'height', '');
  }
  function getChildContainingRectFromElement(container, options, ghostEl) {
    var rect = {};
    Array.from(container.children).forEach(function (child) {
      var _rect$left, _rect$top, _rect$right, _rect$bottom;
      if (!closest(child, options.draggable, container, false) || child.animated || child === ghostEl) return;
      var childRect = getRect(child);
      rect.left = Math.min((_rect$left = rect.left) !== null && _rect$left !== void 0 ? _rect$left : Infinity, childRect.left);
      rect.top = Math.min((_rect$top = rect.top) !== null && _rect$top !== void 0 ? _rect$top : Infinity, childRect.top);
      rect.right = Math.max((_rect$right = rect.right) !== null && _rect$right !== void 0 ? _rect$right : -Infinity, childRect.right);
      rect.bottom = Math.max((_rect$bottom = rect.bottom) !== null && _rect$bottom !== void 0 ? _rect$bottom : -Infinity, childRect.bottom);
    });
    rect.width = rect.right - rect.left;
    rect.height = rect.bottom - rect.top;
    rect.x = rect.left;
    rect.y = rect.top;
    return rect;
  }
  var expando = 'Sortable' + new Date().getTime();

  function AnimationStateManager() {
    var animationStates = [],
      animationCallbackId;
    return {
      captureAnimationState: function captureAnimationState() {
        animationStates = [];
        if (!this.options.animation) return;
        var children = [].slice.call(this.el.children);
        children.forEach(function (child) {
          if (css(child, 'display') === 'none' || child === Sortable.ghost) return;
          animationStates.push({
            target: child,
            rect: getRect(child)
          });
          var fromRect = _objectSpread2({}, animationStates[animationStates.length - 1].rect);


          if (child.thisAnimationDuration) {
            var childMatrix = matrix(child, true);
            if (childMatrix) {
              fromRect.top -= childMatrix.f;
              fromRect.left -= childMatrix.e;
            }
          }
          child.fromRect = fromRect;
        });
      },
      addAnimationState: function addAnimationState(state) {
        animationStates.push(state);
      },
      removeAnimationState: function removeAnimationState(target) {
        animationStates.splice(indexOfObject(animationStates, {
          target: target
        }), 1);
      },
      animateAll: function animateAll(callback) {
        var _this = this;
        if (!this.options.animation) {
          clearTimeout(animationCallbackId);
          if (typeof callback === 'function') callback();
          return;
        }
        var animating = false,
          animationTime = 0;
        animationStates.forEach(function (state) {
          var time = 0,
            target = state.target,
            fromRect = target.fromRect,
            toRect = getRect(target),
            prevFromRect = target.prevFromRect,
            prevToRect = target.prevToRect,
            animatingRect = state.rect,
            targetMatrix = matrix(target, true);
          if (targetMatrix) {

            toRect.top -= targetMatrix.f;
            toRect.left -= targetMatrix.e;
          }
          target.toRect = toRect;
          if (target.thisAnimationDuration) {

            if (isRectEqual(prevFromRect, toRect) && !isRectEqual(fromRect, toRect) &&

            (animatingRect.top - toRect.top) / (animatingRect.left - toRect.left) === (fromRect.top - toRect.top) / (fromRect.left - toRect.left)) {

              time = calculateRealTime(animatingRect, prevFromRect, prevToRect, _this.options);
            }
          }


          if (!isRectEqual(toRect, fromRect)) {
            target.prevFromRect = fromRect;
            target.prevToRect = toRect;
            if (!time) {
              time = _this.options.animation;
            }
            _this.animate(target, animatingRect, toRect, time);
          }
          if (time) {
            animating = true;
            animationTime = Math.max(animationTime, time);
            clearTimeout(target.animationResetTimer);
            target.animationResetTimer = setTimeout(function () {
              target.animationTime = 0;
              target.prevFromRect = null;
              target.fromRect = null;
              target.prevToRect = null;
              target.thisAnimationDuration = null;
            }, time);
            target.thisAnimationDuration = time;
          }
        });
        clearTimeout(animationCallbackId);
        if (!animating) {
          if (typeof callback === 'function') callback();
        } else {
          animationCallbackId = setTimeout(function () {
            if (typeof callback === 'function') callback();
          }, animationTime);
        }
        animationStates = [];
      },
      animate: function animate(target, currentRect, toRect, duration) {
        if (duration) {
          css(target, 'transition', '');
          css(target, 'transform', '');
          var elMatrix = matrix(this.el),
            scaleX = elMatrix && elMatrix.a,
            scaleY = elMatrix && elMatrix.d,
            translateX = (currentRect.left - toRect.left) / (scaleX || 1),
            translateY = (currentRect.top - toRect.top) / (scaleY || 1);
          target.animatingX = !!translateX;
          target.animatingY = !!translateY;
          css(target, 'transform', 'translate3d(' + translateX + 'px,' + translateY + 'px,0)');
          this.forRepaintDummy = repaint(target);

          css(target, 'transition', 'transform ' + duration + 'ms' + (this.options.easing ? ' ' + this.options.easing : ''));
          css(target, 'transform', 'translate3d(0,0,0)');
          typeof target.animated === 'number' && clearTimeout(target.animated);
          target.animated = setTimeout(function () {
            css(target, 'transition', '');
            css(target, 'transform', '');
            target.animated = false;
            target.animatingX = false;
            target.animatingY = false;
          }, duration);
        }
      }
    };
  }
  function repaint(target) {
    return target.offsetWidth;
  }
  function calculateRealTime(animatingRect, fromRect, toRect, options) {
    return Math.sqrt(Math.pow(fromRect.top - animatingRect.top, 2) + Math.pow(fromRect.left - animatingRect.left, 2)) / Math.sqrt(Math.pow(fromRect.top - toRect.top, 2) + Math.pow(fromRect.left - toRect.left, 2)) * options.animation;
  }

  var plugins = [];
  var defaults = {
    initializeByDefault: true
  };
  var PluginManager = {
    mount: function mount(plugin) {

      for (var option in defaults) {
        if (defaults.hasOwnProperty(option) && !(option in plugin)) {
          plugin[option] = defaults[option];
        }
      }
      plugins.forEach(function (p) {
        if (p.pluginName === plugin.pluginName) {
          throw "Sortable: Cannot mount plugin ".concat(plugin.pluginName, " more than once");
        }
      });
      plugins.push(plugin);
    },
    pluginEvent: function pluginEvent(eventName, sortable, evt) {
      var _this = this;
      this.eventCanceled = false;
      evt.cancel = function () {
        _this.eventCanceled = true;
      };
      var eventNameGlobal = eventName + 'Global';
      plugins.forEach(function (plugin) {
        if (!sortable[plugin.pluginName]) return;

        if (sortable[plugin.pluginName][eventNameGlobal]) {
          sortable[plugin.pluginName][eventNameGlobal](_objectSpread2({
            sortable: sortable
          }, evt));
        }



        if (sortable.options[plugin.pluginName] && sortable[plugin.pluginName][eventName]) {
          sortable[plugin.pluginName][eventName](_objectSpread2({
            sortable: sortable
          }, evt));
        }
      });
    },
    initializePlugins: function initializePlugins(sortable, el, defaults, options) {
      plugins.forEach(function (plugin) {
        var pluginName = plugin.pluginName;
        if (!sortable.options[pluginName] && !plugin.initializeByDefault) return;
        var initialized = new plugin(sortable, el, sortable.options);
        initialized.sortable = sortable;
        initialized.options = sortable.options;
        sortable[pluginName] = initialized;


        _extends(defaults, initialized.defaults);
      });
      for (var option in sortable.options) {
        if (!sortable.options.hasOwnProperty(option)) continue;
        var modified = this.modifyOption(sortable, option, sortable.options[option]);
        if (typeof modified !== 'undefined') {
          sortable.options[option] = modified;
        }
      }
    },
    getEventProperties: function getEventProperties(name, sortable) {
      var eventProperties = {};
      plugins.forEach(function (plugin) {
        if (typeof plugin.eventProperties !== 'function') return;
        _extends(eventProperties, plugin.eventProperties.call(sortable[plugin.pluginName], name));
      });
      return eventProperties;
    },
    modifyOption: function modifyOption(sortable, name, value) {
      var modifiedValue;
      plugins.forEach(function (plugin) {

        if (!sortable[plugin.pluginName]) return;


        if (plugin.optionListeners && typeof plugin.optionListeners[name] === 'function') {
          modifiedValue = plugin.optionListeners[name].call(sortable[plugin.pluginName], value);
        }
      });
      return modifiedValue;
    }
  };

  function dispatchEvent(_ref) {
    var sortable = _ref.sortable,
      rootEl = _ref.rootEl,
      name = _ref.name,
      targetEl = _ref.targetEl,
      cloneEl = _ref.cloneEl,
      toEl = _ref.toEl,
      fromEl = _ref.fromEl,
      oldIndex = _ref.oldIndex,
      newIndex = _ref.newIndex,
      oldDraggableIndex = _ref.oldDraggableIndex,
      newDraggableIndex = _ref.newDraggableIndex,
      originalEvent = _ref.originalEvent,
      putSortable = _ref.putSortable,
      extraEventProperties = _ref.extraEventProperties;
    sortable = sortable || rootEl && rootEl[expando];
    if (!sortable) return;
    var evt,
      options = sortable.options,
      onName = 'on' + name.charAt(0).toUpperCase() + name.substr(1);

    if (window.CustomEvent && !IE11OrLess && !Edge) {
      evt = new CustomEvent(name, {
        bubbles: true,
        cancelable: true
      });
    } else {
      evt = document.createEvent('Event');
      evt.initEvent(name, true, true);
    }
    evt.to = toEl || rootEl;
    evt.from = fromEl || rootEl;
    evt.item = targetEl || rootEl;
    evt.clone = cloneEl;
    evt.oldIndex = oldIndex;
    evt.newIndex = newIndex;
    evt.oldDraggableIndex = oldDraggableIndex;
    evt.newDraggableIndex = newDraggableIndex;
    evt.originalEvent = originalEvent;
    evt.pullMode = putSortable ? putSortable.lastPutMode : undefined;
    var allEventProperties = _objectSpread2(_objectSpread2({}, extraEventProperties), PluginManager.getEventProperties(name, sortable));
    for (var option in allEventProperties) {
      evt[option] = allEventProperties[option];
    }
    if (rootEl) {
      rootEl.dispatchEvent(evt);
    }
    if (options[onName]) {
      options[onName].call(sortable, evt);
    }
  }

  var _excluded = ["evt"];
  var pluginEvent = function pluginEvent(eventName, sortable) {
    var _ref = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {},
      originalEvent = _ref.evt,
      data = _objectWithoutProperties(_ref, _excluded);
    PluginManager.pluginEvent.bind(Sortable)(eventName, sortable, _objectSpread2({
      dragEl: dragEl,
      parentEl: parentEl,
      ghostEl: ghostEl,
      rootEl: rootEl,
      nextEl: nextEl,
      lastDownEl: lastDownEl,
      cloneEl: cloneEl,
      cloneHidden: cloneHidden,
      dragStarted: moved,
      putSortable: putSortable,
      activeSortable: Sortable.active,
      originalEvent: originalEvent,
      oldIndex: oldIndex,
      oldDraggableIndex: oldDraggableIndex,
      newIndex: newIndex,
      newDraggableIndex: newDraggableIndex,
      hideGhostForTarget: _hideGhostForTarget,
      unhideGhostForTarget: _unhideGhostForTarget,
      cloneNowHidden: function cloneNowHidden() {
        cloneHidden = true;
      },
      cloneNowShown: function cloneNowShown() {
        cloneHidden = false;
      },
      dispatchSortableEvent: function dispatchSortableEvent(name) {
        _dispatchEvent({
          sortable: sortable,
          name: name,
          originalEvent: originalEvent
        });
      }
    }, data));
  };
  function _dispatchEvent(info) {
    dispatchEvent(_objectSpread2({
      putSortable: putSortable,
      cloneEl: cloneEl,
      targetEl: dragEl,
      rootEl: rootEl,
      oldIndex: oldIndex,
      oldDraggableIndex: oldDraggableIndex,
      newIndex: newIndex,
      newDraggableIndex: newDraggableIndex
    }, info));
  }
  var dragEl,
    parentEl,
    ghostEl,
    rootEl,
    nextEl,
    lastDownEl,
    cloneEl,
    cloneHidden,
    oldIndex,
    newIndex,
    oldDraggableIndex,
    newDraggableIndex,
    activeGroup,
    putSortable,
    awaitingDragStarted = false,
    ignoreNextClick = false,
    sortables = [],
    tapEvt,
    touchEvt,
    lastDx,
    lastDy,
    tapDistanceLeft,
    tapDistanceTop,
    moved,
    lastTarget,
    lastDirection,
    pastFirstInvertThresh = false,
    isCircumstantialInvert = false,
    targetMoveDistance,

    ghostRelativeParent,
    ghostRelativeParentInitialScroll = [],


    _silent = false,
    savedInputChecked = [];


  var documentExists = typeof document !== 'undefined',
    PositionGhostAbsolutely = IOS,
    CSSFloatProperty = Edge || IE11OrLess ? 'cssFloat' : 'float',

    supportDraggable = documentExists && !ChromeForAndroid && !IOS && 'draggable' in document.createElement('div'),
    supportCssPointerEvents = function () {
      if (!documentExists) return;

      if (IE11OrLess) {
        return false;
      }
      var el = document.createElement('x');
      el.style.cssText = 'pointer-events:auto';
      return el.style.pointerEvents === 'auto';
    }(),
    _detectDirection = function _detectDirection(el, options) {
      var elCSS = css(el),
        elWidth = parseInt(elCSS.width) - parseInt(elCSS.paddingLeft) - parseInt(elCSS.paddingRight) - parseInt(elCSS.borderLeftWidth) - parseInt(elCSS.borderRightWidth),
        child1 = getChild(el, 0, options),
        child2 = getChild(el, 1, options),
        firstChildCSS = child1 && css(child1),
        secondChildCSS = child2 && css(child2),
        firstChildWidth = firstChildCSS && parseInt(firstChildCSS.marginLeft) + parseInt(firstChildCSS.marginRight) + getRect(child1).width,
        secondChildWidth = secondChildCSS && parseInt(secondChildCSS.marginLeft) + parseInt(secondChildCSS.marginRight) + getRect(child2).width;
      if (elCSS.display === 'flex') {
        return elCSS.flexDirection === 'column' || elCSS.flexDirection === 'column-reverse' ? 'vertical' : 'horizontal';
      }
      if (elCSS.display === 'grid') {
        return elCSS.gridTemplateColumns.split(' ').length <= 1 ? 'vertical' : 'horizontal';
      }
      if (child1 && firstChildCSS["float"] && firstChildCSS["float"] !== 'none') {
        var touchingSideChild2 = firstChildCSS["float"] === 'left' ? 'left' : 'right';
        return child2 && (secondChildCSS.clear === 'both' || secondChildCSS.clear === touchingSideChild2) ? 'vertical' : 'horizontal';
      }
      return child1 && (firstChildCSS.display === 'block' || firstChildCSS.display === 'flex' || firstChildCSS.display === 'table' || firstChildCSS.display === 'grid' || firstChildWidth >= elWidth && elCSS[CSSFloatProperty] === 'none' || child2 && elCSS[CSSFloatProperty] === 'none' && firstChildWidth + secondChildWidth > elWidth) ? 'vertical' : 'horizontal';
    },
    _dragElInRowColumn = function _dragElInRowColumn(dragRect, targetRect, vertical) {
      var dragElS1Opp = vertical ? dragRect.left : dragRect.top,
        dragElS2Opp = vertical ? dragRect.right : dragRect.bottom,
        dragElOppLength = vertical ? dragRect.width : dragRect.height,
        targetS1Opp = vertical ? targetRect.left : targetRect.top,
        targetS2Opp = vertical ? targetRect.right : targetRect.bottom,
        targetOppLength = vertical ? targetRect.width : targetRect.height;
      return dragElS1Opp === targetS1Opp || dragElS2Opp === targetS2Opp || dragElS1Opp + dragElOppLength / 2 === targetS1Opp + targetOppLength / 2;
    },

    _detectNearestEmptySortable = function _detectNearestEmptySortable(x, y) {
      var ret;
      sortables.some(function (sortable) {
        var threshold = sortable[expando].options.emptyInsertThreshold;
        if (!threshold || lastChild(sortable)) return;
        var rect = getRect(sortable),
          insideHorizontally = x >= rect.left - threshold && x <= rect.right + threshold,
          insideVertically = y >= rect.top - threshold && y <= rect.bottom + threshold;
        if (insideHorizontally && insideVertically) {
          return ret = sortable;
        }
      });
      return ret;
    },
    _prepareGroup = function _prepareGroup(options) {
      function toFn(value, pull) {
        return function (to, from, dragEl, evt) {
          var sameGroup = to.options.group.name && from.options.group.name && to.options.group.name === from.options.group.name;
          if (value == null && (pull || sameGroup)) {


            return true;
          } else if (value == null || value === false) {
            return false;
          } else if (pull && value === 'clone') {
            return value;
          } else if (typeof value === 'function') {
            return toFn(value(to, from, dragEl, evt), pull)(to, from, dragEl, evt);
          } else {
            var otherGroup = (pull ? to : from).options.group.name;
            return value === true || typeof value === 'string' && value === otherGroup || value.join && value.indexOf(otherGroup) > -1;
          }
        };
      }
      var group = {};
      var originalGroup = options.group;
      if (!originalGroup || _typeof(originalGroup) != 'object') {
        originalGroup = {
          name: originalGroup
        };
      }
      group.name = originalGroup.name;
      group.checkPull = toFn(originalGroup.pull, true);
      group.checkPut = toFn(originalGroup.put);
      group.revertClone = originalGroup.revertClone;
      options.group = group;
    },
    _hideGhostForTarget = function _hideGhostForTarget() {
      if (!supportCssPointerEvents && ghostEl) {
        css(ghostEl, 'display', 'none');
      }
    },
    _unhideGhostForTarget = function _unhideGhostForTarget() {
      if (!supportCssPointerEvents && ghostEl) {
        css(ghostEl, 'display', '');
      }
    };


  if (documentExists && !ChromeForAndroid) {
    document.addEventListener('click', function (evt) {
      if (ignoreNextClick) {
        evt.preventDefault();
        evt.stopPropagation && evt.stopPropagation();
        evt.stopImmediatePropagation && evt.stopImmediatePropagation();
        ignoreNextClick = false;
        return false;
      }
    }, true);
  }
  var nearestEmptyInsertDetectEvent = function nearestEmptyInsertDetectEvent(evt) {
    if (dragEl) {
      evt = evt.touches ? evt.touches[0] : evt;
      var nearest = _detectNearestEmptySortable(evt.clientX, evt.clientY);
      if (nearest) {

        var event = {};
        for (var i in evt) {
          if (evt.hasOwnProperty(i)) {
            event[i] = evt[i];
          }
        }
        event.target = event.rootEl = nearest;
        event.preventDefault = void 0;
        event.stopPropagation = void 0;
        nearest[expando]._onDragOver(event);
      }
    }
  };
  var _checkOutsideTargetEl = function _checkOutsideTargetEl(evt) {
    if (dragEl) {
      dragEl.parentNode[expando]._isOutsideThisEl(evt.target);
    }
  };


  function Sortable(el, options) {
    if (!(el && el.nodeType && el.nodeType === 1)) {
      throw "Sortable: `el` must be an HTMLElement, not ".concat({}.toString.call(el));
    }
    this.el = el;
    this.options = options = _extends({}, options);


    el[expando] = this;
    var defaults = {
      group: null,
      sort: true,
      disabled: false,
      store: null,
      handle: null,
      draggable: /^[uo]l$/i.test(el.nodeName) ? '>li' : '>*',
      swapThreshold: 1,

      invertSwap: false,

      invertedSwapThreshold: null,

      removeCloneOnHide: true,
      direction: function direction() {
        return _detectDirection(el, this.options);
      },
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      dragClass: 'sortable-drag',
      ignore: 'a, img',
      filter: null,
      preventOnFilter: true,
      animation: 0,
      easing: null,
      setData: function setData(dataTransfer, dragEl) {
        dataTransfer.setData('Text', dragEl.textContent);
      },
      dropBubble: false,
      dragoverBubble: false,
      dataIdAttr: 'data-id',
      delay: 0,
      delayOnTouchOnly: false,
      touchStartThreshold: (Number.parseInt ? Number : window).parseInt(window.devicePixelRatio, 10) || 1,
      forceFallback: false,
      fallbackClass: 'sortable-fallback',
      fallbackOnBody: false,
      fallbackTolerance: 0,
      fallbackOffset: {
        x: 0,
        y: 0
      },
      supportPointer: Sortable.supportPointer !== false && 'PointerEvent' in window && !Safari,
      emptyInsertThreshold: 5
    };
    PluginManager.initializePlugins(this, el, defaults);


    for (var name in defaults) {
      !(name in options) && (options[name] = defaults[name]);
    }
    _prepareGroup(options);


    for (var fn in this) {
      if (fn.charAt(0) === '_' && typeof this[fn] === 'function') {
        this[fn] = this[fn].bind(this);
      }
    }


    this.nativeDraggable = options.forceFallback ? false : supportDraggable;
    if (this.nativeDraggable) {

      this.options.touchStartThreshold = 1;
    }


    if (options.supportPointer) {
      on(el, 'pointerdown', this._onTapStart);
    } else {
      on(el, 'mousedown', this._onTapStart);
      on(el, 'touchstart', this._onTapStart);
    }
    if (this.nativeDraggable) {
      on(el, 'dragover', this);
      on(el, 'dragenter', this);
    }
    sortables.push(this.el);


    options.store && options.store.get && this.sort(options.store.get(this) || []);


    _extends(this, AnimationStateManager());
  }
  Sortable.prototype = {
    constructor: Sortable,
    _isOutsideThisEl: function _isOutsideThisEl(target) {
      if (!this.el.contains(target) && target !== this.el) {
        lastTarget = null;
      }
    },
    _getDirection: function _getDirection(evt, target) {
      return typeof this.options.direction === 'function' ? this.options.direction.call(this, evt, target, dragEl) : this.options.direction;
    },
    _onTapStart: function _onTapStart( evt) {
      if (!evt.cancelable) return;
      var _this = this,
        el = this.el,
        options = this.options,
        preventOnFilter = options.preventOnFilter,
        type = evt.type,
        touch = evt.touches && evt.touches[0] || evt.pointerType && evt.pointerType === 'touch' && evt,
        target = (touch || evt).target,
        originalTarget = evt.target.shadowRoot && (evt.path && evt.path[0] || evt.composedPath && evt.composedPath()[0]) || target,
        filter = options.filter;
      _saveInputCheckedState(el);


      if (dragEl) {
        return;
      }
      if (/mousedown|pointerdown/.test(type) && evt.button !== 0 || options.disabled) {
        return;
      }


      if (originalTarget.isContentEditable) {
        return;
      }


      if (!this.nativeDraggable && Safari && target && target.tagName.toUpperCase() === 'SELECT') {
        return;
      }
      target = closest(target, options.draggable, el, false);
      if (target && target.animated) {
        return;
      }
      if (lastDownEl === target) {

        return;
      }


      oldIndex = index(target);
      oldDraggableIndex = index(target, options.draggable);


      if (typeof filter === 'function') {
        if (filter.call(this, evt, target, this)) {
          _dispatchEvent({
            sortable: _this,
            rootEl: originalTarget,
            name: 'filter',
            targetEl: target,
            toEl: el,
            fromEl: el
          });
          pluginEvent('filter', _this, {
            evt: evt
          });
          preventOnFilter && evt.cancelable && evt.preventDefault();
          return;
        }
      } else if (filter) {
        filter = filter.split(',').some(function (criteria) {
          criteria = closest(originalTarget, criteria.trim(), el, false);
          if (criteria) {
            _dispatchEvent({
              sortable: _this,
              rootEl: criteria,
              name: 'filter',
              targetEl: target,
              fromEl: el,
              toEl: el
            });
            pluginEvent('filter', _this, {
              evt: evt
            });
            return true;
          }
        });
        if (filter) {
          preventOnFilter && evt.cancelable && evt.preventDefault();
          return;
        }
      }
      if (options.handle && !closest(originalTarget, options.handle, el, false)) {
        return;
      }


      this._prepareDragStart(evt, touch, target);
    },
    _prepareDragStart: function _prepareDragStart( evt, touch, target) {
      var _this = this,
        el = _this.el,
        options = _this.options,
        ownerDocument = el.ownerDocument,
        dragStartFn;
      if (target && !dragEl && target.parentNode === el) {
        var dragRect = getRect(target);
        rootEl = el;
        dragEl = target;
        parentEl = dragEl.parentNode;
        nextEl = dragEl.nextSibling;
        lastDownEl = target;
        activeGroup = options.group;
        Sortable.dragged = dragEl;
        tapEvt = {
          target: dragEl,
          clientX: (touch || evt).clientX,
          clientY: (touch || evt).clientY
        };
        tapDistanceLeft = tapEvt.clientX - dragRect.left;
        tapDistanceTop = tapEvt.clientY - dragRect.top;
        this._lastX = (touch || evt).clientX;
        this._lastY = (touch || evt).clientY;
        dragEl.style['will-change'] = 'all';
        dragStartFn = function dragStartFn() {
          pluginEvent('delayEnded', _this, {
            evt: evt
          });
          if (Sortable.eventCanceled) {
            _this._onDrop();
            return;
          }


          _this._disableDelayedDragEvents();
          if (!FireFox && _this.nativeDraggable) {
            dragEl.draggable = true;
          }


          _this._triggerDragStart(evt, touch);


          _dispatchEvent({
            sortable: _this,
            name: 'choose',
            originalEvent: evt
          });


          toggleClass(dragEl, options.chosenClass, true);
        };


        options.ignore.split(',').forEach(function (criteria) {
          find(dragEl, criteria.trim(), _disableDraggable);
        });
        on(ownerDocument, 'dragover', nearestEmptyInsertDetectEvent);
        on(ownerDocument, 'mousemove', nearestEmptyInsertDetectEvent);
        on(ownerDocument, 'touchmove', nearestEmptyInsertDetectEvent);
        on(ownerDocument, 'mouseup', _this._onDrop);
        on(ownerDocument, 'touchend', _this._onDrop);
        on(ownerDocument, 'touchcancel', _this._onDrop);


        if (FireFox && this.nativeDraggable) {
          this.options.touchStartThreshold = 4;
          dragEl.draggable = true;
        }
        pluginEvent('delayStart', this, {
          evt: evt
        });


        if (options.delay && (!options.delayOnTouchOnly || touch) && (!this.nativeDraggable || !(Edge || IE11OrLess))) {
          if (Sortable.eventCanceled) {
            this._onDrop();
            return;
          }



          on(ownerDocument, 'mouseup', _this._disableDelayedDrag);
          on(ownerDocument, 'touchend', _this._disableDelayedDrag);
          on(ownerDocument, 'touchcancel', _this._disableDelayedDrag);
          on(ownerDocument, 'mousemove', _this._delayedDragTouchMoveHandler);
          on(ownerDocument, 'touchmove', _this._delayedDragTouchMoveHandler);
          options.supportPointer && on(ownerDocument, 'pointermove', _this._delayedDragTouchMoveHandler);
          _this._dragStartTimer = setTimeout(dragStartFn, options.delay);
        } else {
          dragStartFn();
        }
      }
    },
    _delayedDragTouchMoveHandler: function _delayedDragTouchMoveHandler( e) {
      var touch = e.touches ? e.touches[0] : e;
      if (Math.max(Math.abs(touch.clientX - this._lastX), Math.abs(touch.clientY - this._lastY)) >= Math.floor(this.options.touchStartThreshold / (this.nativeDraggable && window.devicePixelRatio || 1))) {
        this._disableDelayedDrag();
      }
    },
    _disableDelayedDrag: function _disableDelayedDrag() {
      dragEl && _disableDraggable(dragEl);
      clearTimeout(this._dragStartTimer);
      this._disableDelayedDragEvents();
    },
    _disableDelayedDragEvents: function _disableDelayedDragEvents() {
      var ownerDocument = this.el.ownerDocument;
      off(ownerDocument, 'mouseup', this._disableDelayedDrag);
      off(ownerDocument, 'touchend', this._disableDelayedDrag);
      off(ownerDocument, 'touchcancel', this._disableDelayedDrag);
      off(ownerDocument, 'mousemove', this._delayedDragTouchMoveHandler);
      off(ownerDocument, 'touchmove', this._delayedDragTouchMoveHandler);
      off(ownerDocument, 'pointermove', this._delayedDragTouchMoveHandler);
    },
    _triggerDragStart: function _triggerDragStart( evt, touch) {
      touch = touch || evt.pointerType == 'touch' && evt;
      if (!this.nativeDraggable || touch) {
        if (this.options.supportPointer) {
          on(document, 'pointermove', this._onTouchMove);
        } else if (touch) {
          on(document, 'touchmove', this._onTouchMove);
        } else {
          on(document, 'mousemove', this._onTouchMove);
        }
      } else {
        on(dragEl, 'dragend', this);
        on(rootEl, 'dragstart', this._onDragStart);
      }
      try {
        if (document.selection) {

          _nextTick(function () {
            document.selection.empty();
          });
        } else {
          window.getSelection().removeAllRanges();
        }
      } catch (err) {}
    },
    _dragStarted: function _dragStarted(fallback, evt) {
      awaitingDragStarted = false;
      if (rootEl && dragEl) {
        pluginEvent('dragStarted', this, {
          evt: evt
        });
        if (this.nativeDraggable) {
          on(document, 'dragover', _checkOutsideTargetEl);
        }
        var options = this.options;


        !fallback && toggleClass(dragEl, options.dragClass, false);
        toggleClass(dragEl, options.ghostClass, true);
        Sortable.active = this;
        fallback && this._appendGhost();


        _dispatchEvent({
          sortable: this,
          name: 'start',
          originalEvent: evt
        });
      } else {
        this._nulling();
      }
    },
    _emulateDragOver: function _emulateDragOver() {
      if (touchEvt) {
        this._lastX = touchEvt.clientX;
        this._lastY = touchEvt.clientY;
        _hideGhostForTarget();
        var target = document.elementFromPoint(touchEvt.clientX, touchEvt.clientY);
        var parent = target;
        while (target && target.shadowRoot) {
          target = target.shadowRoot.elementFromPoint(touchEvt.clientX, touchEvt.clientY);
          if (target === parent) break;
          parent = target;
        }
        dragEl.parentNode[expando]._isOutsideThisEl(target);
        if (parent) {
          do {
            if (parent[expando]) {
              var inserted = void 0;
              inserted = parent[expando]._onDragOver({
                clientX: touchEvt.clientX,
                clientY: touchEvt.clientY,
                target: target,
                rootEl: parent
              });
              if (inserted && !this.options.dragoverBubble) {
                break;
              }
            }
            target = parent;
          }
           while (parent = parent.parentNode);
        }
        _unhideGhostForTarget();
      }
    },
    _onTouchMove: function _onTouchMove( evt) {
      if (tapEvt) {
        var options = this.options,
          fallbackTolerance = options.fallbackTolerance,
          fallbackOffset = options.fallbackOffset,
          touch = evt.touches ? evt.touches[0] : evt,
          ghostMatrix = ghostEl && matrix(ghostEl, true),
          scaleX = ghostEl && ghostMatrix && ghostMatrix.a,
          scaleY = ghostEl && ghostMatrix && ghostMatrix.d,
          relativeScrollOffset = PositionGhostAbsolutely && ghostRelativeParent && getRelativeScrollOffset(ghostRelativeParent),
          dx = (touch.clientX - tapEvt.clientX + fallbackOffset.x) / (scaleX || 1) + (relativeScrollOffset ? relativeScrollOffset[0] - ghostRelativeParentInitialScroll[0] : 0) / (scaleX || 1),
          dy = (touch.clientY - tapEvt.clientY + fallbackOffset.y) / (scaleY || 1) + (relativeScrollOffset ? relativeScrollOffset[1] - ghostRelativeParentInitialScroll[1] : 0) / (scaleY || 1);


        if (!Sortable.active && !awaitingDragStarted) {
          if (fallbackTolerance && Math.max(Math.abs(touch.clientX - this._lastX), Math.abs(touch.clientY - this._lastY)) < fallbackTolerance) {
            return;
          }
          this._onDragStart(evt, true);
        }
        if (ghostEl) {
          if (ghostMatrix) {
            ghostMatrix.e += dx - (lastDx || 0);
            ghostMatrix.f += dy - (lastDy || 0);
          } else {
            ghostMatrix = {
              a: 1,
              b: 0,
              c: 0,
              d: 1,
              e: dx,
              f: dy
            };
          }
          var cssMatrix = "matrix(".concat(ghostMatrix.a, ",").concat(ghostMatrix.b, ",").concat(ghostMatrix.c, ",").concat(ghostMatrix.d, ",").concat(ghostMatrix.e, ",").concat(ghostMatrix.f, ")");
          css(ghostEl, 'webkitTransform', cssMatrix);
          css(ghostEl, 'mozTransform', cssMatrix);
          css(ghostEl, 'msTransform', cssMatrix);
          css(ghostEl, 'transform', cssMatrix);
          lastDx = dx;
          lastDy = dy;
          touchEvt = touch;
        }
        evt.cancelable && evt.preventDefault();
      }
    },
    _appendGhost: function _appendGhost() {


      if (!ghostEl) {
        var container = this.options.fallbackOnBody ? document.body : rootEl,
          rect = getRect(dragEl, true, PositionGhostAbsolutely, true, container),
          options = this.options;


        if (PositionGhostAbsolutely) {

          ghostRelativeParent = container;
          while (css(ghostRelativeParent, 'position') === 'static' && css(ghostRelativeParent, 'transform') === 'none' && ghostRelativeParent !== document) {
            ghostRelativeParent = ghostRelativeParent.parentNode;
          }
          if (ghostRelativeParent !== document.body && ghostRelativeParent !== document.documentElement) {
            if (ghostRelativeParent === document) ghostRelativeParent = getWindowScrollingElement();
            rect.top += ghostRelativeParent.scrollTop;
            rect.left += ghostRelativeParent.scrollLeft;
          } else {
            ghostRelativeParent = getWindowScrollingElement();
          }
          ghostRelativeParentInitialScroll = getRelativeScrollOffset(ghostRelativeParent);
        }
        ghostEl = dragEl.cloneNode(true);
        toggleClass(ghostEl, options.ghostClass, false);
        toggleClass(ghostEl, options.fallbackClass, true);
        toggleClass(ghostEl, options.dragClass, true);
        css(ghostEl, 'transition', '');
        css(ghostEl, 'transform', '');
        css(ghostEl, 'box-sizing', 'border-box');
        css(ghostEl, 'margin', 0);
        css(ghostEl, 'top', rect.top);
        css(ghostEl, 'left', rect.left);
        css(ghostEl, 'width', rect.width);
        css(ghostEl, 'height', rect.height);
        css(ghostEl, 'opacity', '0.8');
        css(ghostEl, 'position', PositionGhostAbsolutely ? 'absolute' : 'fixed');
        css(ghostEl, 'zIndex', '100000');
        css(ghostEl, 'pointerEvents', 'none');
        Sortable.ghost = ghostEl;
        container.appendChild(ghostEl);


        css(ghostEl, 'transform-origin', tapDistanceLeft / parseInt(ghostEl.style.width) * 100 + '% ' + tapDistanceTop / parseInt(ghostEl.style.height) * 100 + '%');
      }
    },
    _onDragStart: function _onDragStart( evt, fallback) {
      var _this = this;
      var dataTransfer = evt.dataTransfer;
      var options = _this.options;
      pluginEvent('dragStart', this, {
        evt: evt
      });
      if (Sortable.eventCanceled) {
        this._onDrop();
        return;
      }
      pluginEvent('setupClone', this);
      if (!Sortable.eventCanceled) {
        cloneEl = clone(dragEl);
        cloneEl.removeAttribute("id");
        cloneEl.draggable = false;
        cloneEl.style['will-change'] = '';
        this._hideClone();
        toggleClass(cloneEl, this.options.chosenClass, false);
        Sortable.clone = cloneEl;
      }


      _this.cloneId = _nextTick(function () {
        pluginEvent('clone', _this);
        if (Sortable.eventCanceled) return;
        if (!_this.options.removeCloneOnHide) {
          rootEl.insertBefore(cloneEl, dragEl);
        }
        _this._hideClone();
        _dispatchEvent({
          sortable: _this,
          name: 'clone'
        });
      });
      !fallback && toggleClass(dragEl, options.dragClass, true);


      if (fallback) {
        ignoreNextClick = true;
        _this._loopId = setInterval(_this._emulateDragOver, 50);
      } else {

        off(document, 'mouseup', _this._onDrop);
        off(document, 'touchend', _this._onDrop);
        off(document, 'touchcancel', _this._onDrop);
        if (dataTransfer) {
          dataTransfer.effectAllowed = 'move';
          options.setData && options.setData.call(_this, dataTransfer, dragEl);
        }
        on(document, 'drop', _this);


        css(dragEl, 'transform', 'translateZ(0)');
      }
      awaitingDragStarted = true;
      _this._dragStartId = _nextTick(_this._dragStarted.bind(_this, fallback, evt));
      on(document, 'selectstart', _this);
      moved = true;
      if (Safari) {
        css(document.body, 'user-select', 'none');
      }
    },

    _onDragOver: function _onDragOver( evt) {
      var el = this.el,
        target = evt.target,
        dragRect,
        targetRect,
        revert,
        options = this.options,
        group = options.group,
        activeSortable = Sortable.active,
        isOwner = activeGroup === group,
        canSort = options.sort,
        fromSortable = putSortable || activeSortable,
        vertical,
        _this = this,
        completedFired = false;
      if (_silent) return;
      function dragOverEvent(name, extra) {
        pluginEvent(name, _this, _objectSpread2({
          evt: evt,
          isOwner: isOwner,
          axis: vertical ? 'vertical' : 'horizontal',
          revert: revert,
          dragRect: dragRect,
          targetRect: targetRect,
          canSort: canSort,
          fromSortable: fromSortable,
          target: target,
          completed: completed,
          onMove: function onMove(target, after) {
            return _onMove(rootEl, el, dragEl, dragRect, target, getRect(target), evt, after);
          },
          changed: changed
        }, extra));
      }


      function capture() {
        dragOverEvent('dragOverAnimationCapture');
        _this.captureAnimationState();
        if (_this !== fromSortable) {
          fromSortable.captureAnimationState();
        }
      }


      function completed(insertion) {
        dragOverEvent('dragOverCompleted', {
          insertion: insertion
        });
        if (insertion) {

          if (isOwner) {
            activeSortable._hideClone();
          } else {
            activeSortable._showClone(_this);
          }
          if (_this !== fromSortable) {

            toggleClass(dragEl, putSortable ? putSortable.options.ghostClass : activeSortable.options.ghostClass, false);
            toggleClass(dragEl, options.ghostClass, true);
          }
          if (putSortable !== _this && _this !== Sortable.active) {
            putSortable = _this;
          } else if (_this === Sortable.active && putSortable) {
            putSortable = null;
          }


          if (fromSortable === _this) {
            _this._ignoreWhileAnimating = target;
          }
          _this.animateAll(function () {
            dragOverEvent('dragOverAnimationComplete');
            _this._ignoreWhileAnimating = null;
          });
          if (_this !== fromSortable) {
            fromSortable.animateAll();
            fromSortable._ignoreWhileAnimating = null;
          }
        }


        if (target === dragEl && !dragEl.animated || target === el && !target.animated) {
          lastTarget = null;
        }


        if (!options.dragoverBubble && !evt.rootEl && target !== document) {
          dragEl.parentNode[expando]._isOutsideThisEl(evt.target);


          !insertion && nearestEmptyInsertDetectEvent(evt);
        }
        !options.dragoverBubble && evt.stopPropagation && evt.stopPropagation();
        return completedFired = true;
      }


      function changed() {
        newIndex = index(dragEl);
        newDraggableIndex = index(dragEl, options.draggable);
        _dispatchEvent({
          sortable: _this,
          name: 'change',
          toEl: el,
          newIndex: newIndex,
          newDraggableIndex: newDraggableIndex,
          originalEvent: evt
        });
      }
      if (evt.preventDefault !== void 0) {
        evt.cancelable && evt.preventDefault();
      }
      target = closest(target, options.draggable, el, true);
      dragOverEvent('dragOver');
      if (Sortable.eventCanceled) return completedFired;
      if (dragEl.contains(evt.target) || target.animated && target.animatingX && target.animatingY || _this._ignoreWhileAnimating === target) {
        return completed(false);
      }
      ignoreNextClick = false;
      if (activeSortable && !options.disabled && (isOwner ? canSort || (revert = parentEl !== rootEl)
      : putSortable === this || (this.lastPutMode = activeGroup.checkPull(this, activeSortable, dragEl, evt)) && group.checkPut(this, activeSortable, dragEl, evt))) {
        vertical = this._getDirection(evt, target) === 'vertical';
        dragRect = getRect(dragEl);
        dragOverEvent('dragOverValid');
        if (Sortable.eventCanceled) return completedFired;
        if (revert) {
          parentEl = rootEl;
          capture();
          this._hideClone();
          dragOverEvent('revert');
          if (!Sortable.eventCanceled) {
            if (nextEl) {
              rootEl.insertBefore(dragEl, nextEl);
            } else {
              rootEl.appendChild(dragEl);
            }
          }
          return completed(true);
        }
        var elLastChild = lastChild(el, options.draggable);
        if (!elLastChild || _ghostIsLast(evt, vertical, this) && !elLastChild.animated) {



          if (elLastChild === dragEl) {
            return completed(false);
          }


          if (elLastChild && el === evt.target) {
            target = elLastChild;
          }
          if (target) {
            targetRect = getRect(target);
          }
          if (_onMove(rootEl, el, dragEl, dragRect, target, targetRect, evt, !!target) !== false) {
            capture();
            if (elLastChild && elLastChild.nextSibling) {

              el.insertBefore(dragEl, elLastChild.nextSibling);
            } else {
              el.appendChild(dragEl);
            }
            parentEl = el;

            changed();
            return completed(true);
          }
        } else if (elLastChild && _ghostIsFirst(evt, vertical, this)) {

          var firstChild = getChild(el, 0, options, true);
          if (firstChild === dragEl) {
            return completed(false);
          }
          target = firstChild;
          targetRect = getRect(target);
          if (_onMove(rootEl, el, dragEl, dragRect, target, targetRect, evt, false) !== false) {
            capture();
            el.insertBefore(dragEl, firstChild);
            parentEl = el;

            changed();
            return completed(true);
          }
        } else if (target.parentNode === el) {
          targetRect = getRect(target);
          var direction = 0,
            targetBeforeFirstSwap,
            differentLevel = dragEl.parentNode !== el,
            differentRowCol = !_dragElInRowColumn(dragEl.animated && dragEl.toRect || dragRect, target.animated && target.toRect || targetRect, vertical),
            side1 = vertical ? 'top' : 'left',
            scrolledPastTop = isScrolledPast(target, 'top', 'top') || isScrolledPast(dragEl, 'top', 'top'),
            scrollBefore = scrolledPastTop ? scrolledPastTop.scrollTop : void 0;
          if (lastTarget !== target) {
            targetBeforeFirstSwap = targetRect[side1];
            pastFirstInvertThresh = false;
            isCircumstantialInvert = !differentRowCol && options.invertSwap || differentLevel;
          }
          direction = _getSwapDirection(evt, target, targetRect, vertical, differentRowCol ? 1 : options.swapThreshold, options.invertedSwapThreshold == null ? options.swapThreshold : options.invertedSwapThreshold, isCircumstantialInvert, lastTarget === target);
          var sibling;
          if (direction !== 0) {

            var dragIndex = index(dragEl);
            do {
              dragIndex -= direction;
              sibling = parentEl.children[dragIndex];
            } while (sibling && (css(sibling, 'display') === 'none' || sibling === ghostEl));
          }

          if (direction === 0 || sibling === target) {
            return completed(false);
          }
          lastTarget = target;
          lastDirection = direction;
          var nextSibling = target.nextElementSibling,
            after = false;
          after = direction === 1;
          var moveVector = _onMove(rootEl, el, dragEl, dragRect, target, targetRect, evt, after);
          if (moveVector !== false) {
            if (moveVector === 1 || moveVector === -1) {
              after = moveVector === 1;
            }
            _silent = true;
            setTimeout(_unsilent, 30);
            capture();
            if (after && !nextSibling) {
              el.appendChild(dragEl);
            } else {
              target.parentNode.insertBefore(dragEl, after ? nextSibling : target);
            }


            if (scrolledPastTop) {
              scrollBy(scrolledPastTop, 0, scrollBefore - scrolledPastTop.scrollTop);
            }
            parentEl = dragEl.parentNode;


            if (targetBeforeFirstSwap !== undefined && !isCircumstantialInvert) {
              targetMoveDistance = Math.abs(targetBeforeFirstSwap - getRect(target)[side1]);
            }
            changed();
            return completed(true);
          }
        }
        if (el.contains(dragEl)) {
          return completed(false);
        }
      }
      return false;
    },
    _ignoreWhileAnimating: null,
    _offMoveEvents: function _offMoveEvents() {
      off(document, 'mousemove', this._onTouchMove);
      off(document, 'touchmove', this._onTouchMove);
      off(document, 'pointermove', this._onTouchMove);
      off(document, 'dragover', nearestEmptyInsertDetectEvent);
      off(document, 'mousemove', nearestEmptyInsertDetectEvent);
      off(document, 'touchmove', nearestEmptyInsertDetectEvent);
    },
    _offUpEvents: function _offUpEvents() {
      var ownerDocument = this.el.ownerDocument;
      off(ownerDocument, 'mouseup', this._onDrop);
      off(ownerDocument, 'touchend', this._onDrop);
      off(ownerDocument, 'pointerup', this._onDrop);
      off(ownerDocument, 'touchcancel', this._onDrop);
      off(document, 'selectstart', this);
    },
    _onDrop: function _onDrop( evt) {
      var el = this.el,
        options = this.options;


      newIndex = index(dragEl);
      newDraggableIndex = index(dragEl, options.draggable);
      pluginEvent('drop', this, {
        evt: evt
      });
      parentEl = dragEl && dragEl.parentNode;


      newIndex = index(dragEl);
      newDraggableIndex = index(dragEl, options.draggable);
      if (Sortable.eventCanceled) {
        this._nulling();
        return;
      }
      awaitingDragStarted = false;
      isCircumstantialInvert = false;
      pastFirstInvertThresh = false;
      clearInterval(this._loopId);
      clearTimeout(this._dragStartTimer);
      _cancelNextTick(this.cloneId);
      _cancelNextTick(this._dragStartId);


      if (this.nativeDraggable) {
        off(document, 'drop', this);
        off(el, 'dragstart', this._onDragStart);
      }
      this._offMoveEvents();
      this._offUpEvents();
      if (Safari) {
        css(document.body, 'user-select', '');
      }
      css(dragEl, 'transform', '');
      if (evt) {
        if (moved) {
          evt.cancelable && evt.preventDefault();
          !options.dropBubble && evt.stopPropagation();
        }
        ghostEl && ghostEl.parentNode && ghostEl.parentNode.removeChild(ghostEl);
        if (rootEl === parentEl || putSortable && putSortable.lastPutMode !== 'clone') {

          cloneEl && cloneEl.parentNode && cloneEl.parentNode.removeChild(cloneEl);
        }
        if (dragEl) {
          if (this.nativeDraggable) {
            off(dragEl, 'dragend', this);
          }
          _disableDraggable(dragEl);
          dragEl.style['will-change'] = '';



          if (moved && !awaitingDragStarted) {
            toggleClass(dragEl, putSortable ? putSortable.options.ghostClass : this.options.ghostClass, false);
          }
          toggleClass(dragEl, this.options.chosenClass, false);


          _dispatchEvent({
            sortable: this,
            name: 'unchoose',
            toEl: parentEl,
            newIndex: null,
            newDraggableIndex: null,
            originalEvent: evt
          });
          if (rootEl !== parentEl) {
            if (newIndex >= 0) {

              _dispatchEvent({
                rootEl: parentEl,
                name: 'add',
                toEl: parentEl,
                fromEl: rootEl,
                originalEvent: evt
              });


              _dispatchEvent({
                sortable: this,
                name: 'remove',
                toEl: parentEl,
                originalEvent: evt
              });


              _dispatchEvent({
                rootEl: parentEl,
                name: 'sort',
                toEl: parentEl,
                fromEl: rootEl,
                originalEvent: evt
              });
              _dispatchEvent({
                sortable: this,
                name: 'sort',
                toEl: parentEl,
                originalEvent: evt
              });
            }
            putSortable && putSortable.save();
          } else {
            if (newIndex !== oldIndex) {
              if (newIndex >= 0) {

                _dispatchEvent({
                  sortable: this,
                  name: 'update',
                  toEl: parentEl,
                  originalEvent: evt
                });
                _dispatchEvent({
                  sortable: this,
                  name: 'sort',
                  toEl: parentEl,
                  originalEvent: evt
                });
              }
            }
          }
          if (Sortable.active) {

            if (newIndex == null || newIndex === -1) {
              newIndex = oldIndex;
              newDraggableIndex = oldDraggableIndex;
            }
            _dispatchEvent({
              sortable: this,
              name: 'end',
              toEl: parentEl,
              originalEvent: evt
            });


            this.save();
          }
        }
      }
      this._nulling();
    },
    _nulling: function _nulling() {
      pluginEvent('nulling', this);
      rootEl = dragEl = parentEl = ghostEl = nextEl = cloneEl = lastDownEl = cloneHidden = tapEvt = touchEvt = moved = newIndex = newDraggableIndex = oldIndex = oldDraggableIndex = lastTarget = lastDirection = putSortable = activeGroup = Sortable.dragged = Sortable.ghost = Sortable.clone = Sortable.active = null;
      savedInputChecked.forEach(function (el) {
        el.checked = true;
      });
      savedInputChecked.length = lastDx = lastDy = 0;
    },
    handleEvent: function handleEvent( evt) {
      switch (evt.type) {
        case 'drop':
        case 'dragend':
          this._onDrop(evt);
          break;
        case 'dragenter':
        case 'dragover':
          if (dragEl) {
            this._onDragOver(evt);
            _globalDragOver(evt);
          }
          break;
        case 'selectstart':
          evt.preventDefault();
          break;
      }
    },

    toArray: function toArray() {
      var order = [],
        el,
        children = this.el.children,
        i = 0,
        n = children.length,
        options = this.options;
      for (; i < n; i++) {
        el = children[i];
        if (closest(el, options.draggable, this.el, false)) {
          order.push(el.getAttribute(options.dataIdAttr) || _generateId(el));
        }
      }
      return order;
    },

    sort: function sort(order, useAnimation) {
      var items = {},
        rootEl = this.el;
      this.toArray().forEach(function (id, i) {
        var el = rootEl.children[i];
        if (closest(el, this.options.draggable, rootEl, false)) {
          items[id] = el;
        }
      }, this);
      useAnimation && this.captureAnimationState();
      order.forEach(function (id) {
        if (items[id]) {
          rootEl.removeChild(items[id]);
          rootEl.appendChild(items[id]);
        }
      });
      useAnimation && this.animateAll();
    },

    save: function save() {
      var store = this.options.store;
      store && store.set && store.set(this);
    },

    closest: function closest$1(el, selector) {
      return closest(el, selector || this.options.draggable, this.el, false);
    },

    option: function option(name, value) {
      var options = this.options;
      if (value === void 0) {
        return options[name];
      } else {
        var modifiedValue = PluginManager.modifyOption(this, name, value);
        if (typeof modifiedValue !== 'undefined') {
          options[name] = modifiedValue;
        } else {
          options[name] = value;
        }
        if (name === 'group') {
          _prepareGroup(options);
        }
      }
    },

    destroy: function destroy() {
      pluginEvent('destroy', this);
      var el = this.el;
      el[expando] = null;
      off(el, 'mousedown', this._onTapStart);
      off(el, 'touchstart', this._onTapStart);
      off(el, 'pointerdown', this._onTapStart);
      if (this.nativeDraggable) {
        off(el, 'dragover', this);
        off(el, 'dragenter', this);
      }

      Array.prototype.forEach.call(el.querySelectorAll('[draggable]'), function (el) {
        el.removeAttribute('draggable');
      });
      this._onDrop();
      this._disableDelayedDragEvents();
      sortables.splice(sortables.indexOf(this.el), 1);
      this.el = el = null;
    },
    _hideClone: function _hideClone() {
      if (!cloneHidden) {
        pluginEvent('hideClone', this);
        if (Sortable.eventCanceled) return;
        css(cloneEl, 'display', 'none');
        if (this.options.removeCloneOnHide && cloneEl.parentNode) {
          cloneEl.parentNode.removeChild(cloneEl);
        }
        cloneHidden = true;
      }
    },
    _showClone: function _showClone(putSortable) {
      if (putSortable.lastPutMode !== 'clone') {
        this._hideClone();
        return;
      }
      if (cloneHidden) {
        pluginEvent('showClone', this);
        if (Sortable.eventCanceled) return;


        if (dragEl.parentNode == rootEl && !this.options.group.revertClone) {
          rootEl.insertBefore(cloneEl, dragEl);
        } else if (nextEl) {
          rootEl.insertBefore(cloneEl, nextEl);
        } else {
          rootEl.appendChild(cloneEl);
        }
        if (this.options.group.revertClone) {
          this.animate(dragEl, cloneEl);
        }
        css(cloneEl, 'display', '');
        cloneHidden = false;
      }
    }
  };
  function _globalDragOver( evt) {
    if (evt.dataTransfer) {
      evt.dataTransfer.dropEffect = 'move';
    }
    evt.cancelable && evt.preventDefault();
  }
  function _onMove(fromEl, toEl, dragEl, dragRect, targetEl, targetRect, originalEvent, willInsertAfter) {
    var evt,
      sortable = fromEl[expando],
      onMoveFn = sortable.options.onMove,
      retVal;

    if (window.CustomEvent && !IE11OrLess && !Edge) {
      evt = new CustomEvent('move', {
        bubbles: true,
        cancelable: true
      });
    } else {
      evt = document.createEvent('Event');
      evt.initEvent('move', true, true);
    }
    evt.to = toEl;
    evt.from = fromEl;
    evt.dragged = dragEl;
    evt.draggedRect = dragRect;
    evt.related = targetEl || toEl;
    evt.relatedRect = targetRect || getRect(toEl);
    evt.willInsertAfter = willInsertAfter;
    evt.originalEvent = originalEvent;
    fromEl.dispatchEvent(evt);
    if (onMoveFn) {
      retVal = onMoveFn.call(sortable, evt, originalEvent);
    }
    return retVal;
  }
  function _disableDraggable(el) {
    el.draggable = false;
  }
  function _unsilent() {
    _silent = false;
  }
  function _ghostIsFirst(evt, vertical, sortable) {
    var firstElRect = getRect(getChild(sortable.el, 0, sortable.options, true));
    var childContainingRect = getChildContainingRectFromElement(sortable.el, sortable.options, ghostEl);
    var spacer = 10;
    return vertical ? evt.clientX < childContainingRect.left - spacer || evt.clientY < firstElRect.top && evt.clientX < firstElRect.right : evt.clientY < childContainingRect.top - spacer || evt.clientY < firstElRect.bottom && evt.clientX < firstElRect.left;
  }
  function _ghostIsLast(evt, vertical, sortable) {
    var lastElRect = getRect(lastChild(sortable.el, sortable.options.draggable));
    var childContainingRect = getChildContainingRectFromElement(sortable.el, sortable.options, ghostEl);
    var spacer = 10;
    return vertical ? evt.clientX > childContainingRect.right + spacer || evt.clientY > lastElRect.bottom && evt.clientX > lastElRect.left : evt.clientY > childContainingRect.bottom + spacer || evt.clientX > lastElRect.right && evt.clientY > lastElRect.top;
  }
  function _getSwapDirection(evt, target, targetRect, vertical, swapThreshold, invertedSwapThreshold, invertSwap, isLastTarget) {
    var mouseOnAxis = vertical ? evt.clientY : evt.clientX,
      targetLength = vertical ? targetRect.height : targetRect.width,
      targetS1 = vertical ? targetRect.top : targetRect.left,
      targetS2 = vertical ? targetRect.bottom : targetRect.right,
      invert = false;
    if (!invertSwap) {

      if (isLastTarget && targetMoveDistance < targetLength * swapThreshold) {


        if (!pastFirstInvertThresh && (lastDirection === 1 ? mouseOnAxis > targetS1 + targetLength * invertedSwapThreshold / 2 : mouseOnAxis < targetS2 - targetLength * invertedSwapThreshold / 2)) {

          pastFirstInvertThresh = true;
        }
        if (!pastFirstInvertThresh) {

          if (lastDirection === 1 ? mouseOnAxis < targetS1 + targetMoveDistance
          : mouseOnAxis > targetS2 - targetMoveDistance) {
            return -lastDirection;
          }
        } else {
          invert = true;
        }
      } else {

        if (mouseOnAxis > targetS1 + targetLength * (1 - swapThreshold) / 2 && mouseOnAxis < targetS2 - targetLength * (1 - swapThreshold) / 2) {
          return _getInsertDirection(target);
        }
      }
    }
    invert = invert || invertSwap;
    if (invert) {

      if (mouseOnAxis < targetS1 + targetLength * invertedSwapThreshold / 2 || mouseOnAxis > targetS2 - targetLength * invertedSwapThreshold / 2) {
        return mouseOnAxis > targetS1 + targetLength / 2 ? 1 : -1;
      }
    }
    return 0;
  }


  function _getInsertDirection(target) {
    if (index(dragEl) < index(target)) {
      return 1;
    } else {
      return -1;
    }
  }


  function _generateId(el) {
    var str = el.tagName + el.className + el.src + el.href + el.textContent,
      i = str.length,
      sum = 0;
    while (i--) {
      sum += str.charCodeAt(i);
    }
    return sum.toString(36);
  }
  function _saveInputCheckedState(root) {
    savedInputChecked.length = 0;
    var inputs = root.getElementsByTagName('input');
    var idx = inputs.length;
    while (idx--) {
      var el = inputs[idx];
      el.checked && savedInputChecked.push(el);
    }
  }
  function _nextTick(fn) {
    return setTimeout(fn, 0);
  }
  function _cancelNextTick(id) {
    return clearTimeout(id);
  }


  if (documentExists) {
    on(document, 'touchmove', function (evt) {
      if ((Sortable.active || awaitingDragStarted) && evt.cancelable) {
        evt.preventDefault();
      }
    });
  }


  Sortable.utils = {
    on: on,
    off: off,
    css: css,
    find: find,
    is: function is(el, selector) {
      return !!closest(el, selector, el, false);
    },
    extend: extend,
    throttle: throttle,
    closest: closest,
    toggleClass: toggleClass,
    clone: clone,
    index: index,
    nextTick: _nextTick,
    cancelNextTick: _cancelNextTick,
    detectDirection: _detectDirection,
    getChild: getChild
  };


  Sortable.get = function (element) {
    return element[expando];
  };


  Sortable.mount = function () {
    for (var _len = arguments.length, plugins = new Array(_len), _key = 0; _key < _len; _key++) {
      plugins[_key] = arguments[_key];
    }
    if (plugins[0].constructor === Array) plugins = plugins[0];
    plugins.forEach(function (plugin) {
      if (!plugin.prototype || !plugin.prototype.constructor) {
        throw "Sortable: Mounted plugin must be a constructor function, not ".concat({}.toString.call(plugin));
      }
      if (plugin.utils) Sortable.utils = _objectSpread2(_objectSpread2({}, Sortable.utils), plugin.utils);
      PluginManager.mount(plugin);
    });
  };


  Sortable.create = function (el, options) {
    return new Sortable(el, options);
  };


  Sortable.version = version;

  var autoScrolls = [],
    scrollEl,
    scrollRootEl,
    scrolling = false,
    lastAutoScrollX,
    lastAutoScrollY,
    touchEvt$1,
    pointerElemChangedInterval;
  function AutoScrollPlugin() {
    function AutoScroll() {
      this.defaults = {
        scroll: true,
        forceAutoScrollFallback: false,
        scrollSensitivity: 30,
        scrollSpeed: 10,
        bubbleScroll: true
      };


      for (var fn in this) {
        if (fn.charAt(0) === '_' && typeof this[fn] === 'function') {
          this[fn] = this[fn].bind(this);
        }
      }
    }
    AutoScroll.prototype = {
      dragStarted: function dragStarted(_ref) {
        var originalEvent = _ref.originalEvent;
        if (this.sortable.nativeDraggable) {
          on(document, 'dragover', this._handleAutoScroll);
        } else {
          if (this.options.supportPointer) {
            on(document, 'pointermove', this._handleFallbackAutoScroll);
          } else if (originalEvent.touches) {
            on(document, 'touchmove', this._handleFallbackAutoScroll);
          } else {
            on(document, 'mousemove', this._handleFallbackAutoScroll);
          }
        }
      },
      dragOverCompleted: function dragOverCompleted(_ref2) {
        var originalEvent = _ref2.originalEvent;

        if (!this.options.dragOverBubble && !originalEvent.rootEl) {
          this._handleAutoScroll(originalEvent);
        }
      },
      drop: function drop() {
        if (this.sortable.nativeDraggable) {
          off(document, 'dragover', this._handleAutoScroll);
        } else {
          off(document, 'pointermove', this._handleFallbackAutoScroll);
          off(document, 'touchmove', this._handleFallbackAutoScroll);
          off(document, 'mousemove', this._handleFallbackAutoScroll);
        }
        clearPointerElemChangedInterval();
        clearAutoScrolls();
        cancelThrottle();
      },
      nulling: function nulling() {
        touchEvt$1 = scrollRootEl = scrollEl = scrolling = pointerElemChangedInterval = lastAutoScrollX = lastAutoScrollY = null;
        autoScrolls.length = 0;
      },
      _handleFallbackAutoScroll: function _handleFallbackAutoScroll(evt) {
        this._handleAutoScroll(evt, true);
      },
      _handleAutoScroll: function _handleAutoScroll(evt, fallback) {
        var _this = this;
        var x = (evt.touches ? evt.touches[0] : evt).clientX,
          y = (evt.touches ? evt.touches[0] : evt).clientY,
          elem = document.elementFromPoint(x, y);
        touchEvt$1 = evt;





        if (fallback || this.options.forceAutoScrollFallback || Edge || IE11OrLess || Safari) {
          autoScroll(evt, this.options, elem, fallback);


          var ogElemScroller = getParentAutoScrollElement(elem, true);
          if (scrolling && (!pointerElemChangedInterval || x !== lastAutoScrollX || y !== lastAutoScrollY)) {
            pointerElemChangedInterval && clearPointerElemChangedInterval();

            pointerElemChangedInterval = setInterval(function () {
              var newElem = getParentAutoScrollElement(document.elementFromPoint(x, y), true);
              if (newElem !== ogElemScroller) {
                ogElemScroller = newElem;
                clearAutoScrolls();
              }
              autoScroll(evt, _this.options, newElem, fallback);
            }, 10);
            lastAutoScrollX = x;
            lastAutoScrollY = y;
          }
        } else {

          if (!this.options.bubbleScroll || getParentAutoScrollElement(elem, true) === getWindowScrollingElement()) {
            clearAutoScrolls();
            return;
          }
          autoScroll(evt, this.options, getParentAutoScrollElement(elem, false), false);
        }
      }
    };
    return _extends(AutoScroll, {
      pluginName: 'scroll',
      initializeByDefault: true
    });
  }
  function clearAutoScrolls() {
    autoScrolls.forEach(function (autoScroll) {
      clearInterval(autoScroll.pid);
    });
    autoScrolls = [];
  }
  function clearPointerElemChangedInterval() {
    clearInterval(pointerElemChangedInterval);
  }
  var autoScroll = throttle(function (evt, options, rootEl, isFallback) {

    if (!options.scroll) return;
    var x = (evt.touches ? evt.touches[0] : evt).clientX,
      y = (evt.touches ? evt.touches[0] : evt).clientY,
      sens = options.scrollSensitivity,
      speed = options.scrollSpeed,
      winScroller = getWindowScrollingElement();
    var scrollThisInstance = false,
      scrollCustomFn;


    if (scrollRootEl !== rootEl) {
      scrollRootEl = rootEl;
      clearAutoScrolls();
      scrollEl = options.scroll;
      scrollCustomFn = options.scrollFn;
      if (scrollEl === true) {
        scrollEl = getParentAutoScrollElement(rootEl, true);
      }
    }
    var layersOut = 0;
    var currentParent = scrollEl;
    do {
      var el = currentParent,
        rect = getRect(el),
        top = rect.top,
        bottom = rect.bottom,
        left = rect.left,
        right = rect.right,
        width = rect.width,
        height = rect.height,
        canScrollX = void 0,
        canScrollY = void 0,
        scrollWidth = el.scrollWidth,
        scrollHeight = el.scrollHeight,
        elCSS = css(el),
        scrollPosX = el.scrollLeft,
        scrollPosY = el.scrollTop;
      if (el === winScroller) {
        canScrollX = width < scrollWidth && (elCSS.overflowX === 'auto' || elCSS.overflowX === 'scroll' || elCSS.overflowX === 'visible');
        canScrollY = height < scrollHeight && (elCSS.overflowY === 'auto' || elCSS.overflowY === 'scroll' || elCSS.overflowY === 'visible');
      } else {
        canScrollX = width < scrollWidth && (elCSS.overflowX === 'auto' || elCSS.overflowX === 'scroll');
        canScrollY = height < scrollHeight && (elCSS.overflowY === 'auto' || elCSS.overflowY === 'scroll');
      }
      var vx = canScrollX && (Math.abs(right - x) <= sens && scrollPosX + width < scrollWidth) - (Math.abs(left - x) <= sens && !!scrollPosX);
      var vy = canScrollY && (Math.abs(bottom - y) <= sens && scrollPosY + height < scrollHeight) - (Math.abs(top - y) <= sens && !!scrollPosY);
      if (!autoScrolls[layersOut]) {
        for (var i = 0; i <= layersOut; i++) {
          if (!autoScrolls[i]) {
            autoScrolls[i] = {};
          }
        }
      }
      if (autoScrolls[layersOut].vx != vx || autoScrolls[layersOut].vy != vy || autoScrolls[layersOut].el !== el) {
        autoScrolls[layersOut].el = el;
        autoScrolls[layersOut].vx = vx;
        autoScrolls[layersOut].vy = vy;
        clearInterval(autoScrolls[layersOut].pid);
        if (vx != 0 || vy != 0) {
          scrollThisInstance = true;

          autoScrolls[layersOut].pid = setInterval(function () {

            if (isFallback && this.layer === 0) {
              Sortable.active._onTouchMove(touchEvt$1);
            }
            var scrollOffsetY = autoScrolls[this.layer].vy ? autoScrolls[this.layer].vy * speed : 0;
            var scrollOffsetX = autoScrolls[this.layer].vx ? autoScrolls[this.layer].vx * speed : 0;
            if (typeof scrollCustomFn === 'function') {
              if (scrollCustomFn.call(Sortable.dragged.parentNode[expando], scrollOffsetX, scrollOffsetY, evt, touchEvt$1, autoScrolls[this.layer].el) !== 'continue') {
                return;
              }
            }
            scrollBy(autoScrolls[this.layer].el, scrollOffsetX, scrollOffsetY);
          }.bind({
            layer: layersOut
          }), 24);
        }
      }
      layersOut++;
    } while (options.bubbleScroll && currentParent !== winScroller && (currentParent = getParentAutoScrollElement(currentParent, false)));
    scrolling = scrollThisInstance;
  }, 30);

  var drop = function drop(_ref) {
    var originalEvent = _ref.originalEvent,
      putSortable = _ref.putSortable,
      dragEl = _ref.dragEl,
      activeSortable = _ref.activeSortable,
      dispatchSortableEvent = _ref.dispatchSortableEvent,
      hideGhostForTarget = _ref.hideGhostForTarget,
      unhideGhostForTarget = _ref.unhideGhostForTarget;
    if (!originalEvent) return;
    var toSortable = putSortable || activeSortable;
    hideGhostForTarget();
    var touch = originalEvent.changedTouches && originalEvent.changedTouches.length ? originalEvent.changedTouches[0] : originalEvent;
    var target = document.elementFromPoint(touch.clientX, touch.clientY);
    unhideGhostForTarget();
    if (toSortable && !toSortable.el.contains(target)) {
      dispatchSortableEvent('spill');
      this.onSpill({
        dragEl: dragEl,
        putSortable: putSortable
      });
    }
  };
  function Revert() {}
  Revert.prototype = {
    startIndex: null,
    dragStart: function dragStart(_ref2) {
      var oldDraggableIndex = _ref2.oldDraggableIndex;
      this.startIndex = oldDraggableIndex;
    },
    onSpill: function onSpill(_ref3) {
      var dragEl = _ref3.dragEl,
        putSortable = _ref3.putSortable;
      this.sortable.captureAnimationState();
      if (putSortable) {
        putSortable.captureAnimationState();
      }
      var nextSibling = getChild(this.sortable.el, this.startIndex, this.options);
      if (nextSibling) {
        this.sortable.el.insertBefore(dragEl, nextSibling);
      } else {
        this.sortable.el.appendChild(dragEl);
      }
      this.sortable.animateAll();
      if (putSortable) {
        putSortable.animateAll();
      }
    },
    drop: drop
  };
  _extends(Revert, {
    pluginName: 'revertOnSpill'
  });
  function Remove() {}
  Remove.prototype = {
    onSpill: function onSpill(_ref4) {
      var dragEl = _ref4.dragEl,
        putSortable = _ref4.putSortable;
      var parentSortable = putSortable || this.sortable;
      parentSortable.captureAnimationState();
      dragEl.parentNode && dragEl.parentNode.removeChild(dragEl);
      parentSortable.animateAll();
    },
    drop: drop
  };
  _extends(Remove, {
    pluginName: 'removeOnSpill'
  });

  var lastSwapEl;
  function SwapPlugin() {
    function Swap() {
      this.defaults = {
        swapClass: 'sortable-swap-highlight'
      };
    }
    Swap.prototype = {
      dragStart: function dragStart(_ref) {
        var dragEl = _ref.dragEl;
        lastSwapEl = dragEl;
      },
      dragOverValid: function dragOverValid(_ref2) {
        var completed = _ref2.completed,
          target = _ref2.target,
          onMove = _ref2.onMove,
          activeSortable = _ref2.activeSortable,
          changed = _ref2.changed,
          cancel = _ref2.cancel;
        if (!activeSortable.options.swap) return;
        var el = this.sortable.el,
          options = this.options;
        if (target && target !== el) {
          var prevSwapEl = lastSwapEl;
          if (onMove(target) !== false) {
            toggleClass(target, options.swapClass, true);
            lastSwapEl = target;
          } else {
            lastSwapEl = null;
          }
          if (prevSwapEl && prevSwapEl !== lastSwapEl) {
            toggleClass(prevSwapEl, options.swapClass, false);
          }
        }
        changed();
        completed(true);
        cancel();
      },
      drop: function drop(_ref3) {
        var activeSortable = _ref3.activeSortable,
          putSortable = _ref3.putSortable,
          dragEl = _ref3.dragEl;
        var toSortable = putSortable || this.sortable;
        var options = this.options;
        lastSwapEl && toggleClass(lastSwapEl, options.swapClass, false);
        if (lastSwapEl && (options.swap || putSortable && putSortable.options.swap)) {
          if (dragEl !== lastSwapEl) {
            toSortable.captureAnimationState();
            if (toSortable !== activeSortable) activeSortable.captureAnimationState();
            swapNodes(dragEl, lastSwapEl);
            toSortable.animateAll();
            if (toSortable !== activeSortable) activeSortable.animateAll();
          }
        }
      },
      nulling: function nulling() {
        lastSwapEl = null;
      }
    };
    return _extends(Swap, {
      pluginName: 'swap',
      eventProperties: function eventProperties() {
        return {
          swapItem: lastSwapEl
        };
      }
    });
  }
  function swapNodes(n1, n2) {
    var p1 = n1.parentNode,
      p2 = n2.parentNode,
      i1,
      i2;
    if (!p1 || !p2 || p1.isEqualNode(n2) || p2.isEqualNode(n1)) return;
    i1 = index(n1);
    i2 = index(n2);
    if (p1.isEqualNode(p2) && i1 < i2) {
      i2++;
    }
    p1.insertBefore(n2, p1.children[i1]);
    p2.insertBefore(n1, p2.children[i2]);
  }

  var multiDragElements = [],
    multiDragClones = [],
    lastMultiDragSelect,

    multiDragSortable,
    initialFolding = false,

    folding = false,

    dragStarted = false,
    dragEl$1,
    clonesFromRect,
    clonesHidden;
  function MultiDragPlugin() {
    function MultiDrag(sortable) {

      for (var fn in this) {
        if (fn.charAt(0) === '_' && typeof this[fn] === 'function') {
          this[fn] = this[fn].bind(this);
        }
      }
      if (!sortable.options.avoidImplicitDeselect) {
        if (sortable.options.supportPointer) {
          on(document, 'pointerup', this._deselectMultiDrag);
        } else {
          on(document, 'mouseup', this._deselectMultiDrag);
          on(document, 'touchend', this._deselectMultiDrag);
        }
      }
      on(document, 'keydown', this._checkKeyDown);
      on(document, 'keyup', this._checkKeyUp);
      this.defaults = {
        selectedClass: 'sortable-selected',
        multiDragKey: null,
        avoidImplicitDeselect: false,
        setData: function setData(dataTransfer, dragEl) {
          var data = '';
          if (multiDragElements.length && multiDragSortable === sortable) {
            multiDragElements.forEach(function (multiDragElement, i) {
              data += (!i ? '' : ', ') + multiDragElement.textContent;
            });
          } else {
            data = dragEl.textContent;
          }
          dataTransfer.setData('Text', data);
        }
      };
    }
    MultiDrag.prototype = {
      multiDragKeyDown: false,
      isMultiDrag: false,
      delayStartGlobal: function delayStartGlobal(_ref) {
        var dragged = _ref.dragEl;
        dragEl$1 = dragged;
      },
      delayEnded: function delayEnded() {
        this.isMultiDrag = ~multiDragElements.indexOf(dragEl$1);
      },
      setupClone: function setupClone(_ref2) {
        var sortable = _ref2.sortable,
          cancel = _ref2.cancel;
        if (!this.isMultiDrag) return;
        for (var i = 0; i < multiDragElements.length; i++) {
          multiDragClones.push(clone(multiDragElements[i]));
          multiDragClones[i].sortableIndex = multiDragElements[i].sortableIndex;
          multiDragClones[i].draggable = false;
          multiDragClones[i].style['will-change'] = '';
          toggleClass(multiDragClones[i], this.options.selectedClass, false);
          multiDragElements[i] === dragEl$1 && toggleClass(multiDragClones[i], this.options.chosenClass, false);
        }
        sortable._hideClone();
        cancel();
      },
      clone: function clone(_ref3) {
        var sortable = _ref3.sortable,
          rootEl = _ref3.rootEl,
          dispatchSortableEvent = _ref3.dispatchSortableEvent,
          cancel = _ref3.cancel;
        if (!this.isMultiDrag) return;
        if (!this.options.removeCloneOnHide) {
          if (multiDragElements.length && multiDragSortable === sortable) {
            insertMultiDragClones(true, rootEl);
            dispatchSortableEvent('clone');
            cancel();
          }
        }
      },
      showClone: function showClone(_ref4) {
        var cloneNowShown = _ref4.cloneNowShown,
          rootEl = _ref4.rootEl,
          cancel = _ref4.cancel;
        if (!this.isMultiDrag) return;
        insertMultiDragClones(false, rootEl);
        multiDragClones.forEach(function (clone) {
          css(clone, 'display', '');
        });
        cloneNowShown();
        clonesHidden = false;
        cancel();
      },
      hideClone: function hideClone(_ref5) {
        var _this = this;
        var sortable = _ref5.sortable,
          cloneNowHidden = _ref5.cloneNowHidden,
          cancel = _ref5.cancel;
        if (!this.isMultiDrag) return;
        multiDragClones.forEach(function (clone) {
          css(clone, 'display', 'none');
          if (_this.options.removeCloneOnHide && clone.parentNode) {
            clone.parentNode.removeChild(clone);
          }
        });
        cloneNowHidden();
        clonesHidden = true;
        cancel();
      },
      dragStartGlobal: function dragStartGlobal(_ref6) {
        var sortable = _ref6.sortable;
        if (!this.isMultiDrag && multiDragSortable) {
          multiDragSortable.multiDrag._deselectMultiDrag();
        }
        multiDragElements.forEach(function (multiDragElement) {
          multiDragElement.sortableIndex = index(multiDragElement);
        });


        multiDragElements = multiDragElements.sort(function (a, b) {
          return a.sortableIndex - b.sortableIndex;
        });
        dragStarted = true;
      },
      dragStarted: function dragStarted(_ref7) {
        var _this2 = this;
        var sortable = _ref7.sortable;
        if (!this.isMultiDrag) return;
        if (this.options.sort) {







          sortable.captureAnimationState();
          if (this.options.animation) {
            multiDragElements.forEach(function (multiDragElement) {
              if (multiDragElement === dragEl$1) return;
              css(multiDragElement, 'position', 'absolute');
            });
            var dragRect = getRect(dragEl$1, false, true, true);
            multiDragElements.forEach(function (multiDragElement) {
              if (multiDragElement === dragEl$1) return;
              setRect(multiDragElement, dragRect);
            });
            folding = true;
            initialFolding = true;
          }
        }
        sortable.animateAll(function () {
          folding = false;
          initialFolding = false;
          if (_this2.options.animation) {
            multiDragElements.forEach(function (multiDragElement) {
              unsetRect(multiDragElement);
            });
          }


          if (_this2.options.sort) {
            removeMultiDragElements();
          }
        });
      },
      dragOver: function dragOver(_ref8) {
        var target = _ref8.target,
          completed = _ref8.completed,
          cancel = _ref8.cancel;
        if (folding && ~multiDragElements.indexOf(target)) {
          completed(false);
          cancel();
        }
      },
      revert: function revert(_ref9) {
        var fromSortable = _ref9.fromSortable,
          rootEl = _ref9.rootEl,
          sortable = _ref9.sortable,
          dragRect = _ref9.dragRect;
        if (multiDragElements.length > 1) {

          multiDragElements.forEach(function (multiDragElement) {
            sortable.addAnimationState({
              target: multiDragElement,
              rect: folding ? getRect(multiDragElement) : dragRect
            });
            unsetRect(multiDragElement);
            multiDragElement.fromRect = dragRect;
            fromSortable.removeAnimationState(multiDragElement);
          });
          folding = false;
          insertMultiDragElements(!this.options.removeCloneOnHide, rootEl);
        }
      },
      dragOverCompleted: function dragOverCompleted(_ref10) {
        var sortable = _ref10.sortable,
          isOwner = _ref10.isOwner,
          insertion = _ref10.insertion,
          activeSortable = _ref10.activeSortable,
          parentEl = _ref10.parentEl,
          putSortable = _ref10.putSortable;
        var options = this.options;
        if (insertion) {

          if (isOwner) {
            activeSortable._hideClone();
          }
          initialFolding = false;

          if (options.animation && multiDragElements.length > 1 && (folding || !isOwner && !activeSortable.options.sort && !putSortable)) {

            var dragRectAbsolute = getRect(dragEl$1, false, true, true);
            multiDragElements.forEach(function (multiDragElement) {
              if (multiDragElement === dragEl$1) return;
              setRect(multiDragElement, dragRectAbsolute);



              parentEl.appendChild(multiDragElement);
            });
            folding = true;
          }


          if (!isOwner) {

            if (!folding) {
              removeMultiDragElements();
            }
            if (multiDragElements.length > 1) {
              var clonesHiddenBefore = clonesHidden;
              activeSortable._showClone(sortable);


              if (activeSortable.options.animation && !clonesHidden && clonesHiddenBefore) {
                multiDragClones.forEach(function (clone) {
                  activeSortable.addAnimationState({
                    target: clone,
                    rect: clonesFromRect
                  });
                  clone.fromRect = clonesFromRect;
                  clone.thisAnimationDuration = null;
                });
              }
            } else {
              activeSortable._showClone(sortable);
            }
          }
        }
      },
      dragOverAnimationCapture: function dragOverAnimationCapture(_ref11) {
        var dragRect = _ref11.dragRect,
          isOwner = _ref11.isOwner,
          activeSortable = _ref11.activeSortable;
        multiDragElements.forEach(function (multiDragElement) {
          multiDragElement.thisAnimationDuration = null;
        });
        if (activeSortable.options.animation && !isOwner && activeSortable.multiDrag.isMultiDrag) {
          clonesFromRect = _extends({}, dragRect);
          var dragMatrix = matrix(dragEl$1, true);
          clonesFromRect.top -= dragMatrix.f;
          clonesFromRect.left -= dragMatrix.e;
        }
      },
      dragOverAnimationComplete: function dragOverAnimationComplete() {
        if (folding) {
          folding = false;
          removeMultiDragElements();
        }
      },
      drop: function drop(_ref12) {
        var evt = _ref12.originalEvent,
          rootEl = _ref12.rootEl,
          parentEl = _ref12.parentEl,
          sortable = _ref12.sortable,
          dispatchSortableEvent = _ref12.dispatchSortableEvent,
          oldIndex = _ref12.oldIndex,
          putSortable = _ref12.putSortable;
        var toSortable = putSortable || this.sortable;
        if (!evt) return;
        var options = this.options,
          children = parentEl.children;


        if (!dragStarted) {
          if (options.multiDragKey && !this.multiDragKeyDown) {
            this._deselectMultiDrag();
          }
          toggleClass(dragEl$1, options.selectedClass, !~multiDragElements.indexOf(dragEl$1));
          if (!~multiDragElements.indexOf(dragEl$1)) {
            multiDragElements.push(dragEl$1);
            dispatchEvent({
              sortable: sortable,
              rootEl: rootEl,
              name: 'select',
              targetEl: dragEl$1,
              originalEvent: evt
            });


            if (evt.shiftKey && lastMultiDragSelect && sortable.el.contains(lastMultiDragSelect)) {
              var lastIndex = index(lastMultiDragSelect),
                currentIndex = index(dragEl$1);
              if (~lastIndex && ~currentIndex && lastIndex !== currentIndex) {


                var n, i;
                if (currentIndex > lastIndex) {
                  i = lastIndex;
                  n = currentIndex;
                } else {
                  i = currentIndex;
                  n = lastIndex + 1;
                }
                for (; i < n; i++) {
                  if (~multiDragElements.indexOf(children[i])) continue;
                  toggleClass(children[i], options.selectedClass, true);
                  multiDragElements.push(children[i]);
                  dispatchEvent({
                    sortable: sortable,
                    rootEl: rootEl,
                    name: 'select',
                    targetEl: children[i],
                    originalEvent: evt
                  });
                }
              }
            } else {
              lastMultiDragSelect = dragEl$1;
            }
            multiDragSortable = toSortable;
          } else {
            multiDragElements.splice(multiDragElements.indexOf(dragEl$1), 1);
            lastMultiDragSelect = null;
            dispatchEvent({
              sortable: sortable,
              rootEl: rootEl,
              name: 'deselect',
              targetEl: dragEl$1,
              originalEvent: evt
            });
          }
        }


        if (dragStarted && this.isMultiDrag) {
          folding = false;

          if ((parentEl[expando].options.sort || parentEl !== rootEl) && multiDragElements.length > 1) {
            var dragRect = getRect(dragEl$1),
              multiDragIndex = index(dragEl$1, ':not(.' + this.options.selectedClass + ')');
            if (!initialFolding && options.animation) dragEl$1.thisAnimationDuration = null;
            toSortable.captureAnimationState();
            if (!initialFolding) {
              if (options.animation) {
                dragEl$1.fromRect = dragRect;
                multiDragElements.forEach(function (multiDragElement) {
                  multiDragElement.thisAnimationDuration = null;
                  if (multiDragElement !== dragEl$1) {
                    var rect = folding ? getRect(multiDragElement) : dragRect;
                    multiDragElement.fromRect = rect;


                    toSortable.addAnimationState({
                      target: multiDragElement,
                      rect: rect
                    });
                  }
                });
              }



              removeMultiDragElements();
              multiDragElements.forEach(function (multiDragElement) {
                if (children[multiDragIndex]) {
                  parentEl.insertBefore(multiDragElement, children[multiDragIndex]);
                } else {
                  parentEl.appendChild(multiDragElement);
                }
                multiDragIndex++;
              });




              if (oldIndex === index(dragEl$1)) {
                var update = false;
                multiDragElements.forEach(function (multiDragElement) {
                  if (multiDragElement.sortableIndex !== index(multiDragElement)) {
                    update = true;
                    return;
                  }
                });
                if (update) {
                  dispatchSortableEvent('update');
                  dispatchSortableEvent('sort');
                }
              }
            }


            multiDragElements.forEach(function (multiDragElement) {
              unsetRect(multiDragElement);
            });
            toSortable.animateAll();
          }
          multiDragSortable = toSortable;
        }


        if (rootEl === parentEl || putSortable && putSortable.lastPutMode !== 'clone') {
          multiDragClones.forEach(function (clone) {
            clone.parentNode && clone.parentNode.removeChild(clone);
          });
        }
      },
      nullingGlobal: function nullingGlobal() {
        this.isMultiDrag = dragStarted = false;
        multiDragClones.length = 0;
      },
      destroyGlobal: function destroyGlobal() {
        this._deselectMultiDrag();
        off(document, 'pointerup', this._deselectMultiDrag);
        off(document, 'mouseup', this._deselectMultiDrag);
        off(document, 'touchend', this._deselectMultiDrag);
        off(document, 'keydown', this._checkKeyDown);
        off(document, 'keyup', this._checkKeyUp);
      },
      _deselectMultiDrag: function _deselectMultiDrag(evt) {
        if (typeof dragStarted !== "undefined" && dragStarted) return;


        if (multiDragSortable !== this.sortable) return;


        if (evt && closest(evt.target, this.options.draggable, this.sortable.el, false)) return;


        if (evt && evt.button !== 0) return;
        while (multiDragElements.length) {
          var el = multiDragElements[0];
          toggleClass(el, this.options.selectedClass, false);
          multiDragElements.shift();
          dispatchEvent({
            sortable: this.sortable,
            rootEl: this.sortable.el,
            name: 'deselect',
            targetEl: el,
            originalEvent: evt
          });
        }
      },
      _checkKeyDown: function _checkKeyDown(evt) {
        if (evt.key === this.options.multiDragKey) {
          this.multiDragKeyDown = true;
        }
      },
      _checkKeyUp: function _checkKeyUp(evt) {
        if (evt.key === this.options.multiDragKey) {
          this.multiDragKeyDown = false;
        }
      }
    };
    return _extends(MultiDrag, {

      pluginName: 'multiDrag',
      utils: {

        select: function select(el) {
          var sortable = el.parentNode[expando];
          if (!sortable || !sortable.options.multiDrag || ~multiDragElements.indexOf(el)) return;
          if (multiDragSortable && multiDragSortable !== sortable) {
            multiDragSortable.multiDrag._deselectMultiDrag();
            multiDragSortable = sortable;
          }
          toggleClass(el, sortable.options.selectedClass, true);
          multiDragElements.push(el);
        },

        deselect: function deselect(el) {
          var sortable = el.parentNode[expando],
            index = multiDragElements.indexOf(el);
          if (!sortable || !sortable.options.multiDrag || !~index) return;
          toggleClass(el, sortable.options.selectedClass, false);
          multiDragElements.splice(index, 1);
        }
      },
      eventProperties: function eventProperties() {
        var _this3 = this;
        var oldIndicies = [],
          newIndicies = [];
        multiDragElements.forEach(function (multiDragElement) {
          oldIndicies.push({
            multiDragElement: multiDragElement,
            index: multiDragElement.sortableIndex
          });


          var newIndex;
          if (folding && multiDragElement !== dragEl$1) {
            newIndex = -1;
          } else if (folding) {
            newIndex = index(multiDragElement, ':not(.' + _this3.options.selectedClass + ')');
          } else {
            newIndex = index(multiDragElement);
          }
          newIndicies.push({
            multiDragElement: multiDragElement,
            index: newIndex
          });
        });
        return {
          items: _toConsumableArray(multiDragElements),
          clones: [].concat(multiDragClones),
          oldIndicies: oldIndicies,
          newIndicies: newIndicies
        };
      },
      optionListeners: {
        multiDragKey: function multiDragKey(key) {
          key = key.toLowerCase();
          if (key === 'ctrl') {
            key = 'Control';
          } else if (key.length > 1) {
            key = key.charAt(0).toUpperCase() + key.substr(1);
          }
          return key;
        }
      }
    });
  }
  function insertMultiDragElements(clonesInserted, rootEl) {
    multiDragElements.forEach(function (multiDragElement, i) {
      var target = rootEl.children[multiDragElement.sortableIndex + (clonesInserted ? Number(i) : 0)];
      if (target) {
        rootEl.insertBefore(multiDragElement, target);
      } else {
        rootEl.appendChild(multiDragElement);
      }
    });
  }


  function insertMultiDragClones(elementsInserted, rootEl) {
    multiDragClones.forEach(function (clone, i) {
      var target = rootEl.children[clone.sortableIndex + (elementsInserted ? Number(i) : 0)];
      if (target) {
        rootEl.insertBefore(clone, target);
      } else {
        rootEl.appendChild(clone);
      }
    });
  }
  function removeMultiDragElements() {
    multiDragElements.forEach(function (multiDragElement) {
      if (multiDragElement === dragEl$1) return;
      multiDragElement.parentNode && multiDragElement.parentNode.removeChild(multiDragElement);
    });
  }

  Sortable.mount(new AutoScrollPlugin());
  Sortable.mount(Remove, Revert);

  Sortable.mount(new SwapPlugin());
  Sortable.mount(new MultiDragPlugin());

  return Sortable;

})));
;





;(function(root, factory) {

  if (typeof define === 'function' && define.amd) {
    define(factory);
  } else if (typeof exports === 'object') {
    module.exports = factory();
  } else {
    root.NProgress = factory();
  }

})(this, function() {
  var NProgress = {};

  NProgress.version = '0.2.0';

  var Settings = NProgress.settings = {
    minimum: 0.08,
    easing: 'ease',
    positionUsing: '',
    speed: 200,
    trickle: true,
    trickleRate: 0.02,
    trickleSpeed: 800,
    showSpinner: true,
    barSelector: '[role="bar"]',
    spinnerSelector: '[role="spinner"]',
    parent: 'body',
    template: '<div class="bar" role="bar"><div class="peg"></div></div><div class="spinner" role="spinner"><div class="spinner-icon"></div></div>'
  };


  NProgress.configure = function(options) {
    var key, value;
    for (key in options) {
      value = options[key];
      if (value !== undefined && options.hasOwnProperty(key)) Settings[key] = value;
    }

    return this;
  };



  NProgress.status = null;



  NProgress.set = function(n) {
    var started = NProgress.isStarted();

    n = clamp(n, Settings.minimum, 1);
    NProgress.status = (n === 1 ? null : n);

    var progress = NProgress.render(!started),
        bar      = progress.querySelector(Settings.barSelector),
        speed    = Settings.speed,
        ease     = Settings.easing;

    progress.offsetWidth;

    queue(function(next) {

      if (Settings.positionUsing === '') Settings.positionUsing = NProgress.getPositioningCSS();


      css(bar, barPositionCSS(n, speed, ease));

      if (n === 1) {

        css(progress, {
          transition: 'none',
          opacity: 1
        });
        progress.offsetWidth;

        setTimeout(function() {
          css(progress, {
            transition: 'all ' + speed + 'ms linear',
            opacity: 0
          });
          setTimeout(function() {
            NProgress.remove();
            next();
          }, speed);
        }, speed);
      } else {
        setTimeout(next, speed);
      }
    });

    return this;
  };

  NProgress.isStarted = function() {
    return typeof NProgress.status === 'number';
  };


  NProgress.start = function() {
    if (!NProgress.status) NProgress.set(0);

    var work = function() {
      setTimeout(function() {
        if (!NProgress.status) return;
        NProgress.trickle();
        work();
      }, Settings.trickleSpeed);
    };

    if (Settings.trickle) work();

    return this;
  };



  NProgress.done = function(force) {
    if (!force && !NProgress.status) return this;

    return NProgress.inc(0.3 + 0.5 * Math.random()).set(1);
  };



  NProgress.inc = function(amount) {
    var n = NProgress.status;

    if (!n) {
      return NProgress.start();
    } else {
      if (typeof amount !== 'number') {
        amount = (1 - n) * clamp(Math.random() * n, 0.1, 0.95);
      }

      n = clamp(n + amount, 0, 0.994);
      return NProgress.set(n);
    }
  };

  NProgress.trickle = function() {
    return NProgress.inc(Math.random() * Settings.trickleRate);
  };


  (function() {
    var initial = 0, current = 0;

    NProgress.promise = function($promise) {
      if (!$promise || $promise.state() === "resolved") {
        return this;
      }

      if (current === 0) {
        NProgress.start();
      }

      initial++;
      current++;

      $promise.always(function() {
        current--;
        if (current === 0) {
            initial = 0;
            NProgress.done();
        } else {
            NProgress.set((initial - current) / initial);
        }
      });

      return this;
    };

  })();



  NProgress.render = function(fromStart) {
    if (NProgress.isRendered()) return document.getElementById('nprogress');

    addClass(document.documentElement, 'nprogress-busy');

    var progress = document.createElement('div');
    progress.id = 'nprogress';
    progress.innerHTML = Settings.template;

    var bar      = progress.querySelector(Settings.barSelector),
        perc     = fromStart ? '-100' : toBarPerc(NProgress.status || 0),
        parent   = document.querySelector(Settings.parent),
        spinner;

    css(bar, {
      transition: 'all 0 linear',
      transform: 'translate3d(' + perc + '%,0,0)'
    });

    if (!Settings.showSpinner) {
      spinner = progress.querySelector(Settings.spinnerSelector);
      spinner && removeElement(spinner);
    }

    if (parent != document.body) {
      addClass(parent, 'nprogress-custom-parent');
    }

    parent.appendChild(progress);
    return progress;
  };



  NProgress.remove = function() {
    removeClass(document.documentElement, 'nprogress-busy');
    removeClass(document.querySelector(Settings.parent), 'nprogress-custom-parent');
    var progress = document.getElementById('nprogress');
    progress && removeElement(progress);
  };



  NProgress.isRendered = function() {
    return !!document.getElementById('nprogress');
  };



  NProgress.getPositioningCSS = function() {

    var bodyStyle = document.body.style;


    var vendorPrefix = ('WebkitTransform' in bodyStyle) ? 'Webkit' :
                       ('MozTransform' in bodyStyle) ? 'Moz' :
                       ('msTransform' in bodyStyle) ? 'ms' :
                       ('OTransform' in bodyStyle) ? 'O' : '';

    if (vendorPrefix + 'Perspective' in bodyStyle) {

      return 'translate3d';
    } else if (vendorPrefix + 'Transform' in bodyStyle) {

      return 'translate';
    } else {

      return 'margin';
    }
  };



  function clamp(n, min, max) {
    if (n < min) return min;
    if (n > max) return max;
    return n;
  }



  function toBarPerc(n) {
    return (-1 + n) * 100;
  }




  function barPositionCSS(n, speed, ease) {
    var barCSS;

    if (Settings.positionUsing === 'translate3d') {
      barCSS = { transform: 'translate3d('+toBarPerc(n)+'%,0,0)' };
    } else if (Settings.positionUsing === 'translate') {
      barCSS = { transform: 'translate('+toBarPerc(n)+'%,0)' };
    } else {
      barCSS = { 'margin-left': toBarPerc(n)+'%' };
    }

    barCSS.transition = 'all '+speed+'ms '+ease;

    return barCSS;
  }



  var queue = (function() {
    var pending = [];

    function next() {
      var fn = pending.shift();
      if (fn) {
        fn(next);
      }
    }

    return function(fn) {
      pending.push(fn);
      if (pending.length == 1) next();
    };
  })();



  var css = (function() {
    var cssPrefixes = [ 'Webkit', 'O', 'Moz', 'ms' ],
        cssProps    = {};

    function camelCase(string) {
      return string.replace(/^-ms-/, 'ms-').replace(/-([\da-z])/gi, function(match, letter) {
        return letter.toUpperCase();
      });
    }

    function getVendorProp(name) {
      var style = document.body.style;
      if (name in style) return name;

      var i = cssPrefixes.length,
          capName = name.charAt(0).toUpperCase() + name.slice(1),
          vendorName;
      while (i--) {
        vendorName = cssPrefixes[i] + capName;
        if (vendorName in style) return vendorName;
      }

      return name;
    }

    function getStyleProp(name) {
      name = camelCase(name);
      return cssProps[name] || (cssProps[name] = getVendorProp(name));
    }

    function applyCss(element, prop, value) {
      prop = getStyleProp(prop);
      element.style[prop] = value;
    }

    return function(element, properties) {
      var args = arguments,
          prop,
          value;

      if (args.length == 2) {
        for (prop in properties) {
          value = properties[prop];
          if (value !== undefined && properties.hasOwnProperty(prop)) applyCss(element, prop, value);
        }
      } else {
        applyCss(element, args[1], args[2]);
      }
    }
  })();



  function hasClass(element, name) {
    var list = typeof element == 'string' ? element : classList(element);
    return list.indexOf(' ' + name + ' ') >= 0;
  }



  function addClass(element, name) {
    var oldList = classList(element),
        newList = oldList + name;

    if (hasClass(oldList, name)) return;


    element.className = newList.substring(1);
  }



  function removeClass(element, name) {
    var oldList = classList(element),
        newList;

    if (!hasClass(element, name)) return;


    newList = oldList.replace(' ' + name + ' ', ' ');


    element.className = newList.substring(1, newList.length - 1);
  }



  function classList(element) {
    return (' ' + (element.className || '') + ' ').replace(/\s+/gi, ' ');
  }



  function removeElement(element) {
    element && element.parentNode && element.parentNode.removeChild(element);
  }

  return NProgress;
});

;





(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.Popper = {}));
}(this, (function (exports) { 'use strict';

  function getWindow(node) {
    if (node == null) {
      return window;
    }

    if (node.toString() !== '[object Window]') {
      var ownerDocument = node.ownerDocument;
      return ownerDocument ? ownerDocument.defaultView || window : window;
    }

    return node;
  }

  function isElement(node) {
    var OwnElement = getWindow(node).Element;
    return node instanceof OwnElement || node instanceof Element;
  }

  function isHTMLElement(node) {
    var OwnElement = getWindow(node).HTMLElement;
    return node instanceof OwnElement || node instanceof HTMLElement;
  }

  function isShadowRoot(node) {

    if (typeof ShadowRoot === 'undefined') {
      return false;
    }

    var OwnElement = getWindow(node).ShadowRoot;
    return node instanceof OwnElement || node instanceof ShadowRoot;
  }

  var max = Math.max;
  var min = Math.min;
  var round = Math.round;

  function getUAString() {
    var uaData = navigator.userAgentData;

    if (uaData != null && uaData.brands && Array.isArray(uaData.brands)) {
      return uaData.brands.map(function (item) {
        return item.brand + "/" + item.version;
      }).join(' ');
    }

    return navigator.userAgent;
  }

  function isLayoutViewport() {
    return !/^((?!chrome|android).)*safari/i.test(getUAString());
  }

  function getBoundingClientRect(element, includeScale, isFixedStrategy) {
    if (includeScale === void 0) {
      includeScale = false;
    }

    if (isFixedStrategy === void 0) {
      isFixedStrategy = false;
    }

    var clientRect = element.getBoundingClientRect();
    var scaleX = 1;
    var scaleY = 1;

    if (includeScale && isHTMLElement(element)) {
      scaleX = element.offsetWidth > 0 ? round(clientRect.width) / element.offsetWidth || 1 : 1;
      scaleY = element.offsetHeight > 0 ? round(clientRect.height) / element.offsetHeight || 1 : 1;
    }

    var _ref = isElement(element) ? getWindow(element) : window,
        visualViewport = _ref.visualViewport;

    var addVisualOffsets = !isLayoutViewport() && isFixedStrategy;
    var x = (clientRect.left + (addVisualOffsets && visualViewport ? visualViewport.offsetLeft : 0)) / scaleX;
    var y = (clientRect.top + (addVisualOffsets && visualViewport ? visualViewport.offsetTop : 0)) / scaleY;
    var width = clientRect.width / scaleX;
    var height = clientRect.height / scaleY;
    return {
      width: width,
      height: height,
      top: y,
      right: x + width,
      bottom: y + height,
      left: x,
      x: x,
      y: y
    };
  }

  function getWindowScroll(node) {
    var win = getWindow(node);
    var scrollLeft = win.pageXOffset;
    var scrollTop = win.pageYOffset;
    return {
      scrollLeft: scrollLeft,
      scrollTop: scrollTop
    };
  }

  function getHTMLElementScroll(element) {
    return {
      scrollLeft: element.scrollLeft,
      scrollTop: element.scrollTop
    };
  }

  function getNodeScroll(node) {
    if (node === getWindow(node) || !isHTMLElement(node)) {
      return getWindowScroll(node);
    } else {
      return getHTMLElementScroll(node);
    }
  }

  function getNodeName(element) {
    return element ? (element.nodeName || '').toLowerCase() : null;
  }

  function getDocumentElement(element) {

    return ((isElement(element) ? element.ownerDocument :
    element.document) || window.document).documentElement;
  }

  function getWindowScrollBarX(element) {







    return getBoundingClientRect(getDocumentElement(element)).left + getWindowScroll(element).scrollLeft;
  }

  function getComputedStyle(element) {
    return getWindow(element).getComputedStyle(element);
  }

  function isScrollParent(element) {

    var _getComputedStyle = getComputedStyle(element),
        overflow = _getComputedStyle.overflow,
        overflowX = _getComputedStyle.overflowX,
        overflowY = _getComputedStyle.overflowY;

    return /auto|scroll|overlay|hidden/.test(overflow + overflowY + overflowX);
  }

  function isElementScaled(element) {
    var rect = element.getBoundingClientRect();
    var scaleX = round(rect.width) / element.offsetWidth || 1;
    var scaleY = round(rect.height) / element.offsetHeight || 1;
    return scaleX !== 1 || scaleY !== 1;
  }



  function getCompositeRect(elementOrVirtualElement, offsetParent, isFixed) {
    if (isFixed === void 0) {
      isFixed = false;
    }

    var isOffsetParentAnElement = isHTMLElement(offsetParent);
    var offsetParentIsScaled = isHTMLElement(offsetParent) && isElementScaled(offsetParent);
    var documentElement = getDocumentElement(offsetParent);
    var rect = getBoundingClientRect(elementOrVirtualElement, offsetParentIsScaled, isFixed);
    var scroll = {
      scrollLeft: 0,
      scrollTop: 0
    };
    var offsets = {
      x: 0,
      y: 0
    };

    if (isOffsetParentAnElement || !isOffsetParentAnElement && !isFixed) {
      if (getNodeName(offsetParent) !== 'body' ||
      isScrollParent(documentElement)) {
        scroll = getNodeScroll(offsetParent);
      }

      if (isHTMLElement(offsetParent)) {
        offsets = getBoundingClientRect(offsetParent, true);
        offsets.x += offsetParent.clientLeft;
        offsets.y += offsetParent.clientTop;
      } else if (documentElement) {
        offsets.x = getWindowScrollBarX(documentElement);
      }
    }

    return {
      x: rect.left + scroll.scrollLeft - offsets.x,
      y: rect.top + scroll.scrollTop - offsets.y,
      width: rect.width,
      height: rect.height
    };
  }



  function getLayoutRect(element) {
    var clientRect = getBoundingClientRect(element);


    var width = element.offsetWidth;
    var height = element.offsetHeight;

    if (Math.abs(clientRect.width - width) <= 1) {
      width = clientRect.width;
    }

    if (Math.abs(clientRect.height - height) <= 1) {
      height = clientRect.height;
    }

    return {
      x: element.offsetLeft,
      y: element.offsetTop,
      width: width,
      height: height
    };
  }

  function getParentNode(element) {
    if (getNodeName(element) === 'html') {
      return element;
    }

    return (


      element.assignedSlot ||
      element.parentNode || (
      isShadowRoot(element) ? element.host : null) ||

      getDocumentElement(element)

    );
  }

  function getScrollParent(node) {
    if (['html', 'body', '#document'].indexOf(getNodeName(node)) >= 0) {

      return node.ownerDocument.body;
    }

    if (isHTMLElement(node) && isScrollParent(node)) {
      return node;
    }

    return getScrollParent(getParentNode(node));
  }



  function listScrollParents(element, list) {
    var _element$ownerDocumen;

    if (list === void 0) {
      list = [];
    }

    var scrollParent = getScrollParent(element);
    var isBody = scrollParent === ((_element$ownerDocumen = element.ownerDocument) == null ? void 0 : _element$ownerDocumen.body);
    var win = getWindow(scrollParent);
    var target = isBody ? [win].concat(win.visualViewport || [], isScrollParent(scrollParent) ? scrollParent : []) : scrollParent;
    var updatedList = list.concat(target);
    return isBody ? updatedList :
    updatedList.concat(listScrollParents(getParentNode(target)));
  }

  function isTableElement(element) {
    return ['table', 'td', 'th'].indexOf(getNodeName(element)) >= 0;
  }

  function getTrueOffsetParent(element) {
    if (!isHTMLElement(element) ||
    getComputedStyle(element).position === 'fixed') {
      return null;
    }

    return element.offsetParent;
  }



  function getContainingBlock(element) {
    var isFirefox = /firefox/i.test(getUAString());
    var isIE = /Trident/i.test(getUAString());

    if (isIE && isHTMLElement(element)) {

      var elementCss = getComputedStyle(element);

      if (elementCss.position === 'fixed') {
        return null;
      }
    }

    var currentNode = getParentNode(element);

    if (isShadowRoot(currentNode)) {
      currentNode = currentNode.host;
    }

    while (isHTMLElement(currentNode) && ['html', 'body'].indexOf(getNodeName(currentNode)) < 0) {
      var css = getComputedStyle(currentNode);



      if (css.transform !== 'none' || css.perspective !== 'none' || css.contain === 'paint' || ['transform', 'perspective'].indexOf(css.willChange) !== -1 || isFirefox && css.willChange === 'filter' || isFirefox && css.filter && css.filter !== 'none') {
        return currentNode;
      } else {
        currentNode = currentNode.parentNode;
      }
    }

    return null;
  }



  function getOffsetParent(element) {
    var window = getWindow(element);
    var offsetParent = getTrueOffsetParent(element);

    while (offsetParent && isTableElement(offsetParent) && getComputedStyle(offsetParent).position === 'static') {
      offsetParent = getTrueOffsetParent(offsetParent);
    }

    if (offsetParent && (getNodeName(offsetParent) === 'html' || getNodeName(offsetParent) === 'body' && getComputedStyle(offsetParent).position === 'static')) {
      return window;
    }

    return offsetParent || getContainingBlock(element) || window;
  }

  var top = 'top';
  var bottom = 'bottom';
  var right = 'right';
  var left = 'left';
  var auto = 'auto';
  var basePlacements = [top, bottom, right, left];
  var start = 'start';
  var end = 'end';
  var clippingParents = 'clippingParents';
  var viewport = 'viewport';
  var popper = 'popper';
  var reference = 'reference';
  var variationPlacements = basePlacements.reduce(function (acc, placement) {
    return acc.concat([placement + "-" + start, placement + "-" + end]);
  }, []);
  var placements = [].concat(basePlacements, [auto]).reduce(function (acc, placement) {
    return acc.concat([placement, placement + "-" + start, placement + "-" + end]);
  }, []);

  var beforeRead = 'beforeRead';
  var read = 'read';
  var afterRead = 'afterRead';

  var beforeMain = 'beforeMain';
  var main = 'main';
  var afterMain = 'afterMain';

  var beforeWrite = 'beforeWrite';
  var write = 'write';
  var afterWrite = 'afterWrite';
  var modifierPhases = [beforeRead, read, afterRead, beforeMain, main, afterMain, beforeWrite, write, afterWrite];

  function order(modifiers) {
    var map = new Map();
    var visited = new Set();
    var result = [];
    modifiers.forEach(function (modifier) {
      map.set(modifier.name, modifier);
    });

    function sort(modifier) {
      visited.add(modifier.name);
      var requires = [].concat(modifier.requires || [], modifier.requiresIfExists || []);
      requires.forEach(function (dep) {
        if (!visited.has(dep)) {
          var depModifier = map.get(dep);

          if (depModifier) {
            sort(depModifier);
          }
        }
      });
      result.push(modifier);
    }

    modifiers.forEach(function (modifier) {
      if (!visited.has(modifier.name)) {

        sort(modifier);
      }
    });
    return result;
  }

  function orderModifiers(modifiers) {

    var orderedModifiers = order(modifiers);

    return modifierPhases.reduce(function (acc, phase) {
      return acc.concat(orderedModifiers.filter(function (modifier) {
        return modifier.phase === phase;
      }));
    }, []);
  }

  function debounce(fn) {
    var pending;
    return function () {
      if (!pending) {
        pending = new Promise(function (resolve) {
          Promise.resolve().then(function () {
            pending = undefined;
            resolve(fn());
          });
        });
      }

      return pending;
    };
  }

  function mergeByName(modifiers) {
    var merged = modifiers.reduce(function (merged, current) {
      var existing = merged[current.name];
      merged[current.name] = existing ? Object.assign({}, existing, current, {
        options: Object.assign({}, existing.options, current.options),
        data: Object.assign({}, existing.data, current.data)
      }) : current;
      return merged;
    }, {});

    return Object.keys(merged).map(function (key) {
      return merged[key];
    });
  }

  function getViewportRect(element, strategy) {
    var win = getWindow(element);
    var html = getDocumentElement(element);
    var visualViewport = win.visualViewport;
    var width = html.clientWidth;
    var height = html.clientHeight;
    var x = 0;
    var y = 0;

    if (visualViewport) {
      width = visualViewport.width;
      height = visualViewport.height;
      var layoutViewport = isLayoutViewport();

      if (layoutViewport || !layoutViewport && strategy === 'fixed') {
        x = visualViewport.offsetLeft;
        y = visualViewport.offsetTop;
      }
    }

    return {
      width: width,
      height: height,
      x: x + getWindowScrollBarX(element),
      y: y
    };
  }



  function getDocumentRect(element) {
    var _element$ownerDocumen;

    var html = getDocumentElement(element);
    var winScroll = getWindowScroll(element);
    var body = (_element$ownerDocumen = element.ownerDocument) == null ? void 0 : _element$ownerDocumen.body;
    var width = max(html.scrollWidth, html.clientWidth, body ? body.scrollWidth : 0, body ? body.clientWidth : 0);
    var height = max(html.scrollHeight, html.clientHeight, body ? body.scrollHeight : 0, body ? body.clientHeight : 0);
    var x = -winScroll.scrollLeft + getWindowScrollBarX(element);
    var y = -winScroll.scrollTop;

    if (getComputedStyle(body || html).direction === 'rtl') {
      x += max(html.clientWidth, body ? body.clientWidth : 0) - width;
    }

    return {
      width: width,
      height: height,
      x: x,
      y: y
    };
  }

  function contains(parent, child) {
    var rootNode = child.getRootNode && child.getRootNode();

    if (parent.contains(child)) {
      return true;
    }
    else if (rootNode && isShadowRoot(rootNode)) {
        var next = child;

        do {
          if (next && parent.isSameNode(next)) {
            return true;
          }


          next = next.parentNode || next.host;
        } while (next);
      }


    return false;
  }

  function rectToClientRect(rect) {
    return Object.assign({}, rect, {
      left: rect.x,
      top: rect.y,
      right: rect.x + rect.width,
      bottom: rect.y + rect.height
    });
  }

  function getInnerBoundingClientRect(element, strategy) {
    var rect = getBoundingClientRect(element, false, strategy === 'fixed');
    rect.top = rect.top + element.clientTop;
    rect.left = rect.left + element.clientLeft;
    rect.bottom = rect.top + element.clientHeight;
    rect.right = rect.left + element.clientWidth;
    rect.width = element.clientWidth;
    rect.height = element.clientHeight;
    rect.x = rect.left;
    rect.y = rect.top;
    return rect;
  }

  function getClientRectFromMixedType(element, clippingParent, strategy) {
    return clippingParent === viewport ? rectToClientRect(getViewportRect(element, strategy)) : isElement(clippingParent) ? getInnerBoundingClientRect(clippingParent, strategy) : rectToClientRect(getDocumentRect(getDocumentElement(element)));
  }




  function getClippingParents(element) {
    var clippingParents = listScrollParents(getParentNode(element));
    var canEscapeClipping = ['absolute', 'fixed'].indexOf(getComputedStyle(element).position) >= 0;
    var clipperElement = canEscapeClipping && isHTMLElement(element) ? getOffsetParent(element) : element;

    if (!isElement(clipperElement)) {
      return [];
    }


    return clippingParents.filter(function (clippingParent) {
      return isElement(clippingParent) && contains(clippingParent, clipperElement) && getNodeName(clippingParent) !== 'body';
    });
  }



  function getClippingRect(element, boundary, rootBoundary, strategy) {
    var mainClippingParents = boundary === 'clippingParents' ? getClippingParents(element) : [].concat(boundary);
    var clippingParents = [].concat(mainClippingParents, [rootBoundary]);
    var firstClippingParent = clippingParents[0];
    var clippingRect = clippingParents.reduce(function (accRect, clippingParent) {
      var rect = getClientRectFromMixedType(element, clippingParent, strategy);
      accRect.top = max(rect.top, accRect.top);
      accRect.right = min(rect.right, accRect.right);
      accRect.bottom = min(rect.bottom, accRect.bottom);
      accRect.left = max(rect.left, accRect.left);
      return accRect;
    }, getClientRectFromMixedType(element, firstClippingParent, strategy));
    clippingRect.width = clippingRect.right - clippingRect.left;
    clippingRect.height = clippingRect.bottom - clippingRect.top;
    clippingRect.x = clippingRect.left;
    clippingRect.y = clippingRect.top;
    return clippingRect;
  }

  function getBasePlacement(placement) {
    return placement.split('-')[0];
  }

  function getVariation(placement) {
    return placement.split('-')[1];
  }

  function getMainAxisFromPlacement(placement) {
    return ['top', 'bottom'].indexOf(placement) >= 0 ? 'x' : 'y';
  }

  function computeOffsets(_ref) {
    var reference = _ref.reference,
        element = _ref.element,
        placement = _ref.placement;
    var basePlacement = placement ? getBasePlacement(placement) : null;
    var variation = placement ? getVariation(placement) : null;
    var commonX = reference.x + reference.width / 2 - element.width / 2;
    var commonY = reference.y + reference.height / 2 - element.height / 2;
    var offsets;

    switch (basePlacement) {
      case top:
        offsets = {
          x: commonX,
          y: reference.y - element.height
        };
        break;

      case bottom:
        offsets = {
          x: commonX,
          y: reference.y + reference.height
        };
        break;

      case right:
        offsets = {
          x: reference.x + reference.width,
          y: commonY
        };
        break;

      case left:
        offsets = {
          x: reference.x - element.width,
          y: commonY
        };
        break;

      default:
        offsets = {
          x: reference.x,
          y: reference.y
        };
    }

    var mainAxis = basePlacement ? getMainAxisFromPlacement(basePlacement) : null;

    if (mainAxis != null) {
      var len = mainAxis === 'y' ? 'height' : 'width';

      switch (variation) {
        case start:
          offsets[mainAxis] = offsets[mainAxis] - (reference[len] / 2 - element[len] / 2);
          break;

        case end:
          offsets[mainAxis] = offsets[mainAxis] + (reference[len] / 2 - element[len] / 2);
          break;
      }
    }

    return offsets;
  }

  function getFreshSideObject() {
    return {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    };
  }

  function mergePaddingObject(paddingObject) {
    return Object.assign({}, getFreshSideObject(), paddingObject);
  }

  function expandToHashMap(value, keys) {
    return keys.reduce(function (hashMap, key) {
      hashMap[key] = value;
      return hashMap;
    }, {});
  }

  function detectOverflow(state, options) {
    if (options === void 0) {
      options = {};
    }

    var _options = options,
        _options$placement = _options.placement,
        placement = _options$placement === void 0 ? state.placement : _options$placement,
        _options$strategy = _options.strategy,
        strategy = _options$strategy === void 0 ? state.strategy : _options$strategy,
        _options$boundary = _options.boundary,
        boundary = _options$boundary === void 0 ? clippingParents : _options$boundary,
        _options$rootBoundary = _options.rootBoundary,
        rootBoundary = _options$rootBoundary === void 0 ? viewport : _options$rootBoundary,
        _options$elementConte = _options.elementContext,
        elementContext = _options$elementConte === void 0 ? popper : _options$elementConte,
        _options$altBoundary = _options.altBoundary,
        altBoundary = _options$altBoundary === void 0 ? false : _options$altBoundary,
        _options$padding = _options.padding,
        padding = _options$padding === void 0 ? 0 : _options$padding;
    var paddingObject = mergePaddingObject(typeof padding !== 'number' ? padding : expandToHashMap(padding, basePlacements));
    var altContext = elementContext === popper ? reference : popper;
    var popperRect = state.rects.popper;
    var element = state.elements[altBoundary ? altContext : elementContext];
    var clippingClientRect = getClippingRect(isElement(element) ? element : element.contextElement || getDocumentElement(state.elements.popper), boundary, rootBoundary, strategy);
    var referenceClientRect = getBoundingClientRect(state.elements.reference);
    var popperOffsets = computeOffsets({
      reference: referenceClientRect,
      element: popperRect,
      strategy: 'absolute',
      placement: placement
    });
    var popperClientRect = rectToClientRect(Object.assign({}, popperRect, popperOffsets));
    var elementClientRect = elementContext === popper ? popperClientRect : referenceClientRect;


    var overflowOffsets = {
      top: clippingClientRect.top - elementClientRect.top + paddingObject.top,
      bottom: elementClientRect.bottom - clippingClientRect.bottom + paddingObject.bottom,
      left: clippingClientRect.left - elementClientRect.left + paddingObject.left,
      right: elementClientRect.right - clippingClientRect.right + paddingObject.right
    };
    var offsetData = state.modifiersData.offset;

    if (elementContext === popper && offsetData) {
      var offset = offsetData[placement];
      Object.keys(overflowOffsets).forEach(function (key) {
        var multiply = [right, bottom].indexOf(key) >= 0 ? 1 : -1;
        var axis = [top, bottom].indexOf(key) >= 0 ? 'y' : 'x';
        overflowOffsets[key] += offset[axis] * multiply;
      });
    }

    return overflowOffsets;
  }

  var DEFAULT_OPTIONS = {
    placement: 'bottom',
    modifiers: [],
    strategy: 'absolute'
  };

  function areValidElements() {
    for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
      args[_key] = arguments[_key];
    }

    return !args.some(function (element) {
      return !(element && typeof element.getBoundingClientRect === 'function');
    });
  }

  function popperGenerator(generatorOptions) {
    if (generatorOptions === void 0) {
      generatorOptions = {};
    }

    var _generatorOptions = generatorOptions,
        _generatorOptions$def = _generatorOptions.defaultModifiers,
        defaultModifiers = _generatorOptions$def === void 0 ? [] : _generatorOptions$def,
        _generatorOptions$def2 = _generatorOptions.defaultOptions,
        defaultOptions = _generatorOptions$def2 === void 0 ? DEFAULT_OPTIONS : _generatorOptions$def2;
    return function createPopper(reference, popper, options) {
      if (options === void 0) {
        options = defaultOptions;
      }

      var state = {
        placement: 'bottom',
        orderedModifiers: [],
        options: Object.assign({}, DEFAULT_OPTIONS, defaultOptions),
        modifiersData: {},
        elements: {
          reference: reference,
          popper: popper
        },
        attributes: {},
        styles: {}
      };
      var effectCleanupFns = [];
      var isDestroyed = false;
      var instance = {
        state: state,
        setOptions: function setOptions(setOptionsAction) {
          var options = typeof setOptionsAction === 'function' ? setOptionsAction(state.options) : setOptionsAction;
          cleanupModifierEffects();
          state.options = Object.assign({}, defaultOptions, state.options, options);
          state.scrollParents = {
            reference: isElement(reference) ? listScrollParents(reference) : reference.contextElement ? listScrollParents(reference.contextElement) : [],
            popper: listScrollParents(popper)
          };


          var orderedModifiers = orderModifiers(mergeByName([].concat(defaultModifiers, state.options.modifiers)));

          state.orderedModifiers = orderedModifiers.filter(function (m) {
            return m.enabled;
          });
          runModifierEffects();
          return instance.update();
        },





        forceUpdate: function forceUpdate() {
          if (isDestroyed) {
            return;
          }

          var _state$elements = state.elements,
              reference = _state$elements.reference,
              popper = _state$elements.popper;


          if (!areValidElements(reference, popper)) {
            return;
          }


          state.rects = {
            reference: getCompositeRect(reference, getOffsetParent(popper), state.options.strategy === 'fixed'),
            popper: getLayoutRect(popper)
          };





          state.reset = false;
          state.placement = state.options.placement;




          state.orderedModifiers.forEach(function (modifier) {
            return state.modifiersData[modifier.name] = Object.assign({}, modifier.data);
          });

          for (var index = 0; index < state.orderedModifiers.length; index++) {
            if (state.reset === true) {
              state.reset = false;
              index = -1;
              continue;
            }

            var _state$orderedModifie = state.orderedModifiers[index],
                fn = _state$orderedModifie.fn,
                _state$orderedModifie2 = _state$orderedModifie.options,
                _options = _state$orderedModifie2 === void 0 ? {} : _state$orderedModifie2,
                name = _state$orderedModifie.name;

            if (typeof fn === 'function') {
              state = fn({
                state: state,
                options: _options,
                name: name,
                instance: instance
              }) || state;
            }
          }
        },


        update: debounce(function () {
          return new Promise(function (resolve) {
            instance.forceUpdate();
            resolve(state);
          });
        }),
        destroy: function destroy() {
          cleanupModifierEffects();
          isDestroyed = true;
        }
      };

      if (!areValidElements(reference, popper)) {
        return instance;
      }

      instance.setOptions(options).then(function (state) {
        if (!isDestroyed && options.onFirstUpdate) {
          options.onFirstUpdate(state);
        }
      });





      function runModifierEffects() {
        state.orderedModifiers.forEach(function (_ref) {
          var name = _ref.name,
              _ref$options = _ref.options,
              options = _ref$options === void 0 ? {} : _ref$options,
              effect = _ref.effect;

          if (typeof effect === 'function') {
            var cleanupFn = effect({
              state: state,
              name: name,
              instance: instance,
              options: options
            });

            var noopFn = function noopFn() {};

            effectCleanupFns.push(cleanupFn || noopFn);
          }
        });
      }

      function cleanupModifierEffects() {
        effectCleanupFns.forEach(function (fn) {
          return fn();
        });
        effectCleanupFns = [];
      }

      return instance;
    };
  }

  var passive = {
    passive: true
  };

  function effect$2(_ref) {
    var state = _ref.state,
        instance = _ref.instance,
        options = _ref.options;
    var _options$scroll = options.scroll,
        scroll = _options$scroll === void 0 ? true : _options$scroll,
        _options$resize = options.resize,
        resize = _options$resize === void 0 ? true : _options$resize;
    var window = getWindow(state.elements.popper);
    var scrollParents = [].concat(state.scrollParents.reference, state.scrollParents.popper);

    if (scroll) {
      scrollParents.forEach(function (scrollParent) {
        scrollParent.addEventListener('scroll', instance.update, passive);
      });
    }

    if (resize) {
      window.addEventListener('resize', instance.update, passive);
    }

    return function () {
      if (scroll) {
        scrollParents.forEach(function (scrollParent) {
          scrollParent.removeEventListener('scroll', instance.update, passive);
        });
      }

      if (resize) {
        window.removeEventListener('resize', instance.update, passive);
      }
    };
  }


  var eventListeners = {
    name: 'eventListeners',
    enabled: true,
    phase: 'write',
    fn: function fn() {},
    effect: effect$2,
    data: {}
  };

  function popperOffsets(_ref) {
    var state = _ref.state,
        name = _ref.name;




    state.modifiersData[name] = computeOffsets({
      reference: state.rects.reference,
      element: state.rects.popper,
      strategy: 'absolute',
      placement: state.placement
    });
  }


  var popperOffsets$1 = {
    name: 'popperOffsets',
    enabled: true,
    phase: 'read',
    fn: popperOffsets,
    data: {}
  };

  var unsetSides = {
    top: 'auto',
    right: 'auto',
    bottom: 'auto',
    left: 'auto'
  };



  function roundOffsetsByDPR(_ref, win) {
    var x = _ref.x,
        y = _ref.y;
    var dpr = win.devicePixelRatio || 1;
    return {
      x: round(x * dpr) / dpr || 0,
      y: round(y * dpr) / dpr || 0
    };
  }

  function mapToStyles(_ref2) {
    var _Object$assign2;

    var popper = _ref2.popper,
        popperRect = _ref2.popperRect,
        placement = _ref2.placement,
        variation = _ref2.variation,
        offsets = _ref2.offsets,
        position = _ref2.position,
        gpuAcceleration = _ref2.gpuAcceleration,
        adaptive = _ref2.adaptive,
        roundOffsets = _ref2.roundOffsets,
        isFixed = _ref2.isFixed;
    var _offsets$x = offsets.x,
        x = _offsets$x === void 0 ? 0 : _offsets$x,
        _offsets$y = offsets.y,
        y = _offsets$y === void 0 ? 0 : _offsets$y;

    var _ref3 = typeof roundOffsets === 'function' ? roundOffsets({
      x: x,
      y: y
    }) : {
      x: x,
      y: y
    };

    x = _ref3.x;
    y = _ref3.y;
    var hasX = offsets.hasOwnProperty('x');
    var hasY = offsets.hasOwnProperty('y');
    var sideX = left;
    var sideY = top;
    var win = window;

    if (adaptive) {
      var offsetParent = getOffsetParent(popper);
      var heightProp = 'clientHeight';
      var widthProp = 'clientWidth';

      if (offsetParent === getWindow(popper)) {
        offsetParent = getDocumentElement(popper);

        if (getComputedStyle(offsetParent).position !== 'static' && position === 'absolute') {
          heightProp = 'scrollHeight';
          widthProp = 'scrollWidth';
        }
      }


      offsetParent = offsetParent;

      if (placement === top || (placement === left || placement === right) && variation === end) {
        sideY = bottom;
        var offsetY = isFixed && offsetParent === win && win.visualViewport ? win.visualViewport.height :
        offsetParent[heightProp];
        y -= offsetY - popperRect.height;
        y *= gpuAcceleration ? 1 : -1;
      }

      if (placement === left || (placement === top || placement === bottom) && variation === end) {
        sideX = right;
        var offsetX = isFixed && offsetParent === win && win.visualViewport ? win.visualViewport.width :
        offsetParent[widthProp];
        x -= offsetX - popperRect.width;
        x *= gpuAcceleration ? 1 : -1;
      }
    }

    var commonStyles = Object.assign({
      position: position
    }, adaptive && unsetSides);

    var _ref4 = roundOffsets === true ? roundOffsetsByDPR({
      x: x,
      y: y
    }, getWindow(popper)) : {
      x: x,
      y: y
    };

    x = _ref4.x;
    y = _ref4.y;

    if (gpuAcceleration) {
      var _Object$assign;

      return Object.assign({}, commonStyles, (_Object$assign = {}, _Object$assign[sideY] = hasY ? '0' : '', _Object$assign[sideX] = hasX ? '0' : '', _Object$assign.transform = (win.devicePixelRatio || 1) <= 1 ? "translate(" + x + "px, " + y + "px)" : "translate3d(" + x + "px, " + y + "px, 0)", _Object$assign));
    }

    return Object.assign({}, commonStyles, (_Object$assign2 = {}, _Object$assign2[sideY] = hasY ? y + "px" : '', _Object$assign2[sideX] = hasX ? x + "px" : '', _Object$assign2.transform = '', _Object$assign2));
  }

  function computeStyles(_ref5) {
    var state = _ref5.state,
        options = _ref5.options;
    var _options$gpuAccelerat = options.gpuAcceleration,
        gpuAcceleration = _options$gpuAccelerat === void 0 ? true : _options$gpuAccelerat,
        _options$adaptive = options.adaptive,
        adaptive = _options$adaptive === void 0 ? true : _options$adaptive,
        _options$roundOffsets = options.roundOffsets,
        roundOffsets = _options$roundOffsets === void 0 ? true : _options$roundOffsets;
    var commonStyles = {
      placement: getBasePlacement(state.placement),
      variation: getVariation(state.placement),
      popper: state.elements.popper,
      popperRect: state.rects.popper,
      gpuAcceleration: gpuAcceleration,
      isFixed: state.options.strategy === 'fixed'
    };

    if (state.modifiersData.popperOffsets != null) {
      state.styles.popper = Object.assign({}, state.styles.popper, mapToStyles(Object.assign({}, commonStyles, {
        offsets: state.modifiersData.popperOffsets,
        position: state.options.strategy,
        adaptive: adaptive,
        roundOffsets: roundOffsets
      })));
    }

    if (state.modifiersData.arrow != null) {
      state.styles.arrow = Object.assign({}, state.styles.arrow, mapToStyles(Object.assign({}, commonStyles, {
        offsets: state.modifiersData.arrow,
        position: 'absolute',
        adaptive: false,
        roundOffsets: roundOffsets
      })));
    }

    state.attributes.popper = Object.assign({}, state.attributes.popper, {
      'data-popper-placement': state.placement
    });
  }


  var computeStyles$1 = {
    name: 'computeStyles',
    enabled: true,
    phase: 'beforeWrite',
    fn: computeStyles,
    data: {}
  };



  function applyStyles(_ref) {
    var state = _ref.state;
    Object.keys(state.elements).forEach(function (name) {
      var style = state.styles[name] || {};
      var attributes = state.attributes[name] || {};
      var element = state.elements[name];

      if (!isHTMLElement(element) || !getNodeName(element)) {
        return;
      }




      Object.assign(element.style, style);
      Object.keys(attributes).forEach(function (name) {
        var value = attributes[name];

        if (value === false) {
          element.removeAttribute(name);
        } else {
          element.setAttribute(name, value === true ? '' : value);
        }
      });
    });
  }

  function effect$1(_ref2) {
    var state = _ref2.state;
    var initialStyles = {
      popper: {
        position: state.options.strategy,
        left: '0',
        top: '0',
        margin: '0'
      },
      arrow: {
        position: 'absolute'
      },
      reference: {}
    };
    Object.assign(state.elements.popper.style, initialStyles.popper);
    state.styles = initialStyles;

    if (state.elements.arrow) {
      Object.assign(state.elements.arrow.style, initialStyles.arrow);
    }

    return function () {
      Object.keys(state.elements).forEach(function (name) {
        var element = state.elements[name];
        var attributes = state.attributes[name] || {};
        var styleProperties = Object.keys(state.styles.hasOwnProperty(name) ? state.styles[name] : initialStyles[name]);

        var style = styleProperties.reduce(function (style, property) {
          style[property] = '';
          return style;
        }, {});

        if (!isHTMLElement(element) || !getNodeName(element)) {
          return;
        }

        Object.assign(element.style, style);
        Object.keys(attributes).forEach(function (attribute) {
          element.removeAttribute(attribute);
        });
      });
    };
  }


  var applyStyles$1 = {
    name: 'applyStyles',
    enabled: true,
    phase: 'write',
    fn: applyStyles,
    effect: effect$1,
    requires: ['computeStyles']
  };

  function distanceAndSkiddingToXY(placement, rects, offset) {
    var basePlacement = getBasePlacement(placement);
    var invertDistance = [left, top].indexOf(basePlacement) >= 0 ? -1 : 1;

    var _ref = typeof offset === 'function' ? offset(Object.assign({}, rects, {
      placement: placement
    })) : offset,
        skidding = _ref[0],
        distance = _ref[1];

    skidding = skidding || 0;
    distance = (distance || 0) * invertDistance;
    return [left, right].indexOf(basePlacement) >= 0 ? {
      x: distance,
      y: skidding
    } : {
      x: skidding,
      y: distance
    };
  }

  function offset(_ref2) {
    var state = _ref2.state,
        options = _ref2.options,
        name = _ref2.name;
    var _options$offset = options.offset,
        offset = _options$offset === void 0 ? [0, 0] : _options$offset;
    var data = placements.reduce(function (acc, placement) {
      acc[placement] = distanceAndSkiddingToXY(placement, state.rects, offset);
      return acc;
    }, {});
    var _data$state$placement = data[state.placement],
        x = _data$state$placement.x,
        y = _data$state$placement.y;

    if (state.modifiersData.popperOffsets != null) {
      state.modifiersData.popperOffsets.x += x;
      state.modifiersData.popperOffsets.y += y;
    }

    state.modifiersData[name] = data;
  }


  var offset$1 = {
    name: 'offset',
    enabled: true,
    phase: 'main',
    requires: ['popperOffsets'],
    fn: offset
  };

  var hash$1 = {
    left: 'right',
    right: 'left',
    bottom: 'top',
    top: 'bottom'
  };
  function getOppositePlacement(placement) {
    return placement.replace(/left|right|bottom|top/g, function (matched) {
      return hash$1[matched];
    });
  }

  var hash = {
    start: 'end',
    end: 'start'
  };
  function getOppositeVariationPlacement(placement) {
    return placement.replace(/start|end/g, function (matched) {
      return hash[matched];
    });
  }

  function computeAutoPlacement(state, options) {
    if (options === void 0) {
      options = {};
    }

    var _options = options,
        placement = _options.placement,
        boundary = _options.boundary,
        rootBoundary = _options.rootBoundary,
        padding = _options.padding,
        flipVariations = _options.flipVariations,
        _options$allowedAutoP = _options.allowedAutoPlacements,
        allowedAutoPlacements = _options$allowedAutoP === void 0 ? placements : _options$allowedAutoP;
    var variation = getVariation(placement);
    var placements$1 = variation ? flipVariations ? variationPlacements : variationPlacements.filter(function (placement) {
      return getVariation(placement) === variation;
    }) : basePlacements;
    var allowedPlacements = placements$1.filter(function (placement) {
      return allowedAutoPlacements.indexOf(placement) >= 0;
    });

    if (allowedPlacements.length === 0) {
      allowedPlacements = placements$1;
    }


    var overflows = allowedPlacements.reduce(function (acc, placement) {
      acc[placement] = detectOverflow(state, {
        placement: placement,
        boundary: boundary,
        rootBoundary: rootBoundary,
        padding: padding
      })[getBasePlacement(placement)];
      return acc;
    }, {});
    return Object.keys(overflows).sort(function (a, b) {
      return overflows[a] - overflows[b];
    });
  }

  function getExpandedFallbackPlacements(placement) {
    if (getBasePlacement(placement) === auto) {
      return [];
    }

    var oppositePlacement = getOppositePlacement(placement);
    return [getOppositeVariationPlacement(placement), oppositePlacement, getOppositeVariationPlacement(oppositePlacement)];
  }

  function flip(_ref) {
    var state = _ref.state,
        options = _ref.options,
        name = _ref.name;

    if (state.modifiersData[name]._skip) {
      return;
    }

    var _options$mainAxis = options.mainAxis,
        checkMainAxis = _options$mainAxis === void 0 ? true : _options$mainAxis,
        _options$altAxis = options.altAxis,
        checkAltAxis = _options$altAxis === void 0 ? true : _options$altAxis,
        specifiedFallbackPlacements = options.fallbackPlacements,
        padding = options.padding,
        boundary = options.boundary,
        rootBoundary = options.rootBoundary,
        altBoundary = options.altBoundary,
        _options$flipVariatio = options.flipVariations,
        flipVariations = _options$flipVariatio === void 0 ? true : _options$flipVariatio,
        allowedAutoPlacements = options.allowedAutoPlacements;
    var preferredPlacement = state.options.placement;
    var basePlacement = getBasePlacement(preferredPlacement);
    var isBasePlacement = basePlacement === preferredPlacement;
    var fallbackPlacements = specifiedFallbackPlacements || (isBasePlacement || !flipVariations ? [getOppositePlacement(preferredPlacement)] : getExpandedFallbackPlacements(preferredPlacement));
    var placements = [preferredPlacement].concat(fallbackPlacements).reduce(function (acc, placement) {
      return acc.concat(getBasePlacement(placement) === auto ? computeAutoPlacement(state, {
        placement: placement,
        boundary: boundary,
        rootBoundary: rootBoundary,
        padding: padding,
        flipVariations: flipVariations,
        allowedAutoPlacements: allowedAutoPlacements
      }) : placement);
    }, []);
    var referenceRect = state.rects.reference;
    var popperRect = state.rects.popper;
    var checksMap = new Map();
    var makeFallbackChecks = true;
    var firstFittingPlacement = placements[0];

    for (var i = 0; i < placements.length; i++) {
      var placement = placements[i];

      var _basePlacement = getBasePlacement(placement);

      var isStartVariation = getVariation(placement) === start;
      var isVertical = [top, bottom].indexOf(_basePlacement) >= 0;
      var len = isVertical ? 'width' : 'height';
      var overflow = detectOverflow(state, {
        placement: placement,
        boundary: boundary,
        rootBoundary: rootBoundary,
        altBoundary: altBoundary,
        padding: padding
      });
      var mainVariationSide = isVertical ? isStartVariation ? right : left : isStartVariation ? bottom : top;

      if (referenceRect[len] > popperRect[len]) {
        mainVariationSide = getOppositePlacement(mainVariationSide);
      }

      var altVariationSide = getOppositePlacement(mainVariationSide);
      var checks = [];

      if (checkMainAxis) {
        checks.push(overflow[_basePlacement] <= 0);
      }

      if (checkAltAxis) {
        checks.push(overflow[mainVariationSide] <= 0, overflow[altVariationSide] <= 0);
      }

      if (checks.every(function (check) {
        return check;
      })) {
        firstFittingPlacement = placement;
        makeFallbackChecks = false;
        break;
      }

      checksMap.set(placement, checks);
    }

    if (makeFallbackChecks) {

      var numberOfChecks = flipVariations ? 3 : 1;

      var _loop = function _loop(_i) {
        var fittingPlacement = placements.find(function (placement) {
          var checks = checksMap.get(placement);

          if (checks) {
            return checks.slice(0, _i).every(function (check) {
              return check;
            });
          }
        });

        if (fittingPlacement) {
          firstFittingPlacement = fittingPlacement;
          return "break";
        }
      };

      for (var _i = numberOfChecks; _i > 0; _i--) {
        var _ret = _loop(_i);

        if (_ret === "break") break;
      }
    }

    if (state.placement !== firstFittingPlacement) {
      state.modifiersData[name]._skip = true;
      state.placement = firstFittingPlacement;
      state.reset = true;
    }
  }


  var flip$1 = {
    name: 'flip',
    enabled: true,
    phase: 'main',
    fn: flip,
    requiresIfExists: ['offset'],
    data: {
      _skip: false
    }
  };

  function getAltAxis(axis) {
    return axis === 'x' ? 'y' : 'x';
  }

  function within(min$1, value, max$1) {
    return max(min$1, min(value, max$1));
  }
  function withinMaxClamp(min, value, max) {
    var v = within(min, value, max);
    return v > max ? max : v;
  }

  function preventOverflow(_ref) {
    var state = _ref.state,
        options = _ref.options,
        name = _ref.name;
    var _options$mainAxis = options.mainAxis,
        checkMainAxis = _options$mainAxis === void 0 ? true : _options$mainAxis,
        _options$altAxis = options.altAxis,
        checkAltAxis = _options$altAxis === void 0 ? false : _options$altAxis,
        boundary = options.boundary,
        rootBoundary = options.rootBoundary,
        altBoundary = options.altBoundary,
        padding = options.padding,
        _options$tether = options.tether,
        tether = _options$tether === void 0 ? true : _options$tether,
        _options$tetherOffset = options.tetherOffset,
        tetherOffset = _options$tetherOffset === void 0 ? 0 : _options$tetherOffset;
    var overflow = detectOverflow(state, {
      boundary: boundary,
      rootBoundary: rootBoundary,
      padding: padding,
      altBoundary: altBoundary
    });
    var basePlacement = getBasePlacement(state.placement);
    var variation = getVariation(state.placement);
    var isBasePlacement = !variation;
    var mainAxis = getMainAxisFromPlacement(basePlacement);
    var altAxis = getAltAxis(mainAxis);
    var popperOffsets = state.modifiersData.popperOffsets;
    var referenceRect = state.rects.reference;
    var popperRect = state.rects.popper;
    var tetherOffsetValue = typeof tetherOffset === 'function' ? tetherOffset(Object.assign({}, state.rects, {
      placement: state.placement
    })) : tetherOffset;
    var normalizedTetherOffsetValue = typeof tetherOffsetValue === 'number' ? {
      mainAxis: tetherOffsetValue,
      altAxis: tetherOffsetValue
    } : Object.assign({
      mainAxis: 0,
      altAxis: 0
    }, tetherOffsetValue);
    var offsetModifierState = state.modifiersData.offset ? state.modifiersData.offset[state.placement] : null;
    var data = {
      x: 0,
      y: 0
    };

    if (!popperOffsets) {
      return;
    }

    if (checkMainAxis) {
      var _offsetModifierState$;

      var mainSide = mainAxis === 'y' ? top : left;
      var altSide = mainAxis === 'y' ? bottom : right;
      var len = mainAxis === 'y' ? 'height' : 'width';
      var offset = popperOffsets[mainAxis];
      var min$1 = offset + overflow[mainSide];
      var max$1 = offset - overflow[altSide];
      var additive = tether ? -popperRect[len] / 2 : 0;
      var minLen = variation === start ? referenceRect[len] : popperRect[len];
      var maxLen = variation === start ? -popperRect[len] : -referenceRect[len];


      var arrowElement = state.elements.arrow;
      var arrowRect = tether && arrowElement ? getLayoutRect(arrowElement) : {
        width: 0,
        height: 0
      };
      var arrowPaddingObject = state.modifiersData['arrow#persistent'] ? state.modifiersData['arrow#persistent'].padding : getFreshSideObject();
      var arrowPaddingMin = arrowPaddingObject[mainSide];
      var arrowPaddingMax = arrowPaddingObject[altSide];





      var arrowLen = within(0, referenceRect[len], arrowRect[len]);
      var minOffset = isBasePlacement ? referenceRect[len] / 2 - additive - arrowLen - arrowPaddingMin - normalizedTetherOffsetValue.mainAxis : minLen - arrowLen - arrowPaddingMin - normalizedTetherOffsetValue.mainAxis;
      var maxOffset = isBasePlacement ? -referenceRect[len] / 2 + additive + arrowLen + arrowPaddingMax + normalizedTetherOffsetValue.mainAxis : maxLen + arrowLen + arrowPaddingMax + normalizedTetherOffsetValue.mainAxis;
      var arrowOffsetParent = state.elements.arrow && getOffsetParent(state.elements.arrow);
      var clientOffset = arrowOffsetParent ? mainAxis === 'y' ? arrowOffsetParent.clientTop || 0 : arrowOffsetParent.clientLeft || 0 : 0;
      var offsetModifierValue = (_offsetModifierState$ = offsetModifierState == null ? void 0 : offsetModifierState[mainAxis]) != null ? _offsetModifierState$ : 0;
      var tetherMin = offset + minOffset - offsetModifierValue - clientOffset;
      var tetherMax = offset + maxOffset - offsetModifierValue;
      var preventedOffset = within(tether ? min(min$1, tetherMin) : min$1, offset, tether ? max(max$1, tetherMax) : max$1);
      popperOffsets[mainAxis] = preventedOffset;
      data[mainAxis] = preventedOffset - offset;
    }

    if (checkAltAxis) {
      var _offsetModifierState$2;

      var _mainSide = mainAxis === 'x' ? top : left;

      var _altSide = mainAxis === 'x' ? bottom : right;

      var _offset = popperOffsets[altAxis];

      var _len = altAxis === 'y' ? 'height' : 'width';

      var _min = _offset + overflow[_mainSide];

      var _max = _offset - overflow[_altSide];

      var isOriginSide = [top, left].indexOf(basePlacement) !== -1;

      var _offsetModifierValue = (_offsetModifierState$2 = offsetModifierState == null ? void 0 : offsetModifierState[altAxis]) != null ? _offsetModifierState$2 : 0;

      var _tetherMin = isOriginSide ? _min : _offset - referenceRect[_len] - popperRect[_len] - _offsetModifierValue + normalizedTetherOffsetValue.altAxis;

      var _tetherMax = isOriginSide ? _offset + referenceRect[_len] + popperRect[_len] - _offsetModifierValue - normalizedTetherOffsetValue.altAxis : _max;

      var _preventedOffset = tether && isOriginSide ? withinMaxClamp(_tetherMin, _offset, _tetherMax) : within(tether ? _tetherMin : _min, _offset, tether ? _tetherMax : _max);

      popperOffsets[altAxis] = _preventedOffset;
      data[altAxis] = _preventedOffset - _offset;
    }

    state.modifiersData[name] = data;
  }


  var preventOverflow$1 = {
    name: 'preventOverflow',
    enabled: true,
    phase: 'main',
    fn: preventOverflow,
    requiresIfExists: ['offset']
  };

  var toPaddingObject = function toPaddingObject(padding, state) {
    padding = typeof padding === 'function' ? padding(Object.assign({}, state.rects, {
      placement: state.placement
    })) : padding;
    return mergePaddingObject(typeof padding !== 'number' ? padding : expandToHashMap(padding, basePlacements));
  };

  function arrow(_ref) {
    var _state$modifiersData$;

    var state = _ref.state,
        name = _ref.name,
        options = _ref.options;
    var arrowElement = state.elements.arrow;
    var popperOffsets = state.modifiersData.popperOffsets;
    var basePlacement = getBasePlacement(state.placement);
    var axis = getMainAxisFromPlacement(basePlacement);
    var isVertical = [left, right].indexOf(basePlacement) >= 0;
    var len = isVertical ? 'height' : 'width';

    if (!arrowElement || !popperOffsets) {
      return;
    }

    var paddingObject = toPaddingObject(options.padding, state);
    var arrowRect = getLayoutRect(arrowElement);
    var minProp = axis === 'y' ? top : left;
    var maxProp = axis === 'y' ? bottom : right;
    var endDiff = state.rects.reference[len] + state.rects.reference[axis] - popperOffsets[axis] - state.rects.popper[len];
    var startDiff = popperOffsets[axis] - state.rects.reference[axis];
    var arrowOffsetParent = getOffsetParent(arrowElement);
    var clientSize = arrowOffsetParent ? axis === 'y' ? arrowOffsetParent.clientHeight || 0 : arrowOffsetParent.clientWidth || 0 : 0;
    var centerToReference = endDiff / 2 - startDiff / 2;


    var min = paddingObject[minProp];
    var max = clientSize - arrowRect[len] - paddingObject[maxProp];
    var center = clientSize / 2 - arrowRect[len] / 2 + centerToReference;
    var offset = within(min, center, max);

    var axisProp = axis;
    state.modifiersData[name] = (_state$modifiersData$ = {}, _state$modifiersData$[axisProp] = offset, _state$modifiersData$.centerOffset = offset - center, _state$modifiersData$);
  }

  function effect(_ref2) {
    var state = _ref2.state,
        options = _ref2.options;
    var _options$element = options.element,
        arrowElement = _options$element === void 0 ? '[data-popper-arrow]' : _options$element;

    if (arrowElement == null) {
      return;
    }


    if (typeof arrowElement === 'string') {
      arrowElement = state.elements.popper.querySelector(arrowElement);

      if (!arrowElement) {
        return;
      }
    }

    if (!contains(state.elements.popper, arrowElement)) {
      return;
    }

    state.elements.arrow = arrowElement;
  }


  var arrow$1 = {
    name: 'arrow',
    enabled: true,
    phase: 'main',
    fn: arrow,
    effect: effect,
    requires: ['popperOffsets'],
    requiresIfExists: ['preventOverflow']
  };

  function getSideOffsets(overflow, rect, preventedOffsets) {
    if (preventedOffsets === void 0) {
      preventedOffsets = {
        x: 0,
        y: 0
      };
    }

    return {
      top: overflow.top - rect.height - preventedOffsets.y,
      right: overflow.right - rect.width + preventedOffsets.x,
      bottom: overflow.bottom - rect.height + preventedOffsets.y,
      left: overflow.left - rect.width - preventedOffsets.x
    };
  }

  function isAnySideFullyClipped(overflow) {
    return [top, right, bottom, left].some(function (side) {
      return overflow[side] >= 0;
    });
  }

  function hide(_ref) {
    var state = _ref.state,
        name = _ref.name;
    var referenceRect = state.rects.reference;
    var popperRect = state.rects.popper;
    var preventedOffsets = state.modifiersData.preventOverflow;
    var referenceOverflow = detectOverflow(state, {
      elementContext: 'reference'
    });
    var popperAltOverflow = detectOverflow(state, {
      altBoundary: true
    });
    var referenceClippingOffsets = getSideOffsets(referenceOverflow, referenceRect);
    var popperEscapeOffsets = getSideOffsets(popperAltOverflow, popperRect, preventedOffsets);
    var isReferenceHidden = isAnySideFullyClipped(referenceClippingOffsets);
    var hasPopperEscaped = isAnySideFullyClipped(popperEscapeOffsets);
    state.modifiersData[name] = {
      referenceClippingOffsets: referenceClippingOffsets,
      popperEscapeOffsets: popperEscapeOffsets,
      isReferenceHidden: isReferenceHidden,
      hasPopperEscaped: hasPopperEscaped
    };
    state.attributes.popper = Object.assign({}, state.attributes.popper, {
      'data-popper-reference-hidden': isReferenceHidden,
      'data-popper-escaped': hasPopperEscaped
    });
  }


  var hide$1 = {
    name: 'hide',
    enabled: true,
    phase: 'main',
    requiresIfExists: ['preventOverflow'],
    fn: hide
  };

  var defaultModifiers$1 = [eventListeners, popperOffsets$1, computeStyles$1, applyStyles$1];
  var createPopper$1 = popperGenerator({
    defaultModifiers: defaultModifiers$1
  });

  var defaultModifiers = [eventListeners, popperOffsets$1, computeStyles$1, applyStyles$1, offset$1, flip$1, preventOverflow$1, arrow$1, hide$1];
  var createPopper = popperGenerator({
    defaultModifiers: defaultModifiers
  });

  exports.applyStyles = applyStyles$1;
  exports.arrow = arrow$1;
  exports.computeStyles = computeStyles$1;
  exports.createPopper = createPopper;
  exports.createPopperLite = createPopper$1;
  exports.defaultModifiers = defaultModifiers;
  exports.detectOverflow = detectOverflow;
  exports.eventListeners = eventListeners;
  exports.flip = flip$1;
  exports.hide = hide$1;
  exports.offset = offset$1;
  exports.popperGenerator = popperGenerator;
  exports.popperOffsets = popperOffsets$1;
  exports.preventOverflow = preventOverflow$1;

  Object.defineProperty(exports, '__esModule', { value: true });

})));

;




(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory(require('@popperjs/core')) :
  typeof define === 'function' && define.amd ? define(['@popperjs/core'], factory) :
  (global = global || self, global.tippy = factory(global.Popper));
}(this, (function (core) { 'use strict';

  var css = ".tippy-box[data-animation=fade][data-state=hidden]{opacity:0}[data-tippy-root]{max-width:calc(100vw - 10px)}.tippy-box{position:relative;background-color:#333;color:#fff;border-radius:4px;font-size:14px;line-height:1.4;white-space:normal;outline:0;transition-property:transform,visibility,opacity}.tippy-box[data-placement^=top]>.tippy-arrow{bottom:0}.tippy-box[data-placement^=top]>.tippy-arrow:before{bottom:-7px;left:0;border-width:8px 8px 0;border-top-color:initial;transform-origin:center top}.tippy-box[data-placement^=bottom]>.tippy-arrow{top:0}.tippy-box[data-placement^=bottom]>.tippy-arrow:before{top:-7px;left:0;border-width:0 8px 8px;border-bottom-color:initial;transform-origin:center bottom}.tippy-box[data-placement^=left]>.tippy-arrow{right:0}.tippy-box[data-placement^=left]>.tippy-arrow:before{border-width:8px 0 8px 8px;border-left-color:initial;right:-7px;transform-origin:center left}.tippy-box[data-placement^=right]>.tippy-arrow{left:0}.tippy-box[data-placement^=right]>.tippy-arrow:before{left:-7px;border-width:8px 8px 8px 0;border-right-color:initial;transform-origin:center right}.tippy-box[data-inertia][data-state=visible]{transition-timing-function:cubic-bezier(.54,1.5,.38,1.11)}.tippy-arrow{width:16px;height:16px;color:#333}.tippy-arrow:before{content:\"\";position:absolute;border-color:transparent;border-style:solid}.tippy-content{position:relative;padding:5px 9px;z-index:1}";

  function injectCSS(css) {
    var style = document.createElement('style');
    style.textContent = css;
    style.setAttribute('data-tippy-stylesheet', '');
    var head = document.head;
    var firstStyleOrLinkTag = document.querySelector('head>style,head>link');

    if (firstStyleOrLinkTag) {
      head.insertBefore(style, firstStyleOrLinkTag);
    } else {
      head.appendChild(style);
    }
  }

  var isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';
  var isIE11 = isBrowser ?
  !!window.msCrypto : false;

  var ROUND_ARROW = '<svg width="16" height="6" xmlns="http://www.w3.org/2000/svg"><path d="M0 6s1.796-.013 4.67-3.615C5.851.9 6.93.006 8 0c1.07-.006 2.148.887 3.343 2.385C14.233 6.005 16 6 16 6H0z"></svg>';
  var BOX_CLASS = "tippy-box";
  var CONTENT_CLASS = "tippy-content";
  var BACKDROP_CLASS = "tippy-backdrop";
  var ARROW_CLASS = "tippy-arrow";
  var SVG_ARROW_CLASS = "tippy-svg-arrow";
  var TOUCH_OPTIONS = {
    passive: true,
    capture: true
  };
  var TIPPY_DEFAULT_APPEND_TO = function TIPPY_DEFAULT_APPEND_TO() {
    return document.body;
  };

  function hasOwnProperty(obj, key) {
    return {}.hasOwnProperty.call(obj, key);
  }
  function getValueAtIndexOrReturn(value, index, defaultValue) {
    if (Array.isArray(value)) {
      var v = value[index];
      return v == null ? Array.isArray(defaultValue) ? defaultValue[index] : defaultValue : v;
    }

    return value;
  }
  function isType(value, type) {
    var str = {}.toString.call(value);
    return str.indexOf('[object') === 0 && str.indexOf(type + "]") > -1;
  }
  function invokeWithArgsOrReturn(value, args) {
    return typeof value === 'function' ? value.apply(void 0, args) : value;
  }
  function debounce(fn, ms) {

    if (ms === 0) {
      return fn;
    }

    var timeout;
    return function (arg) {
      clearTimeout(timeout);
      timeout = setTimeout(function () {
        fn(arg);
      }, ms);
    };
  }
  function removeProperties(obj, keys) {
    var clone = Object.assign({}, obj);
    keys.forEach(function (key) {
      delete clone[key];
    });
    return clone;
  }
  function splitBySpaces(value) {
    return value.split(/\s+/).filter(Boolean);
  }
  function normalizeToArray(value) {
    return [].concat(value);
  }
  function pushIfUnique(arr, value) {
    if (arr.indexOf(value) === -1) {
      arr.push(value);
    }
  }
  function unique(arr) {
    return arr.filter(function (item, index) {
      return arr.indexOf(item) === index;
    });
  }
  function getBasePlacement(placement) {
    return placement.split('-')[0];
  }
  function arrayFrom(value) {
    return [].slice.call(value);
  }
  function removeUndefinedProps(obj) {
    return Object.keys(obj).reduce(function (acc, key) {
      if (obj[key] !== undefined) {
        acc[key] = obj[key];
      }

      return acc;
    }, {});
  }

  function div() {
    return document.createElement('div');
  }
  function isElement(value) {
    return ['Element', 'Fragment'].some(function (type) {
      return isType(value, type);
    });
  }
  function isNodeList(value) {
    return isType(value, 'NodeList');
  }
  function isMouseEvent(value) {
    return isType(value, 'MouseEvent');
  }
  function isReferenceElement(value) {
    return !!(value && value._tippy && value._tippy.reference === value);
  }
  function getArrayOfElements(value) {
    if (isElement(value)) {
      return [value];
    }

    if (isNodeList(value)) {
      return arrayFrom(value);
    }

    if (Array.isArray(value)) {
      return value;
    }

    return arrayFrom(document.querySelectorAll(value));
  }
  function setTransitionDuration(els, value) {
    els.forEach(function (el) {
      if (el) {
        el.style.transitionDuration = value + "ms";
      }
    });
  }
  function setVisibilityState(els, state) {
    els.forEach(function (el) {
      if (el) {
        el.setAttribute('data-state', state);
      }
    });
  }
  function getOwnerDocument(elementOrElements) {
    var _element$ownerDocumen;

    var _normalizeToArray = normalizeToArray(elementOrElements),
        element = _normalizeToArray[0];


    return element != null && (_element$ownerDocumen = element.ownerDocument) != null && _element$ownerDocumen.body ? element.ownerDocument : document;
  }
  function isCursorOutsideInteractiveBorder(popperTreeData, event) {
    var clientX = event.clientX,
        clientY = event.clientY;
    return popperTreeData.every(function (_ref) {
      var popperRect = _ref.popperRect,
          popperState = _ref.popperState,
          props = _ref.props;
      var interactiveBorder = props.interactiveBorder;
      var basePlacement = getBasePlacement(popperState.placement);
      var offsetData = popperState.modifiersData.offset;

      if (!offsetData) {
        return true;
      }

      var topDistance = basePlacement === 'bottom' ? offsetData.top.y : 0;
      var bottomDistance = basePlacement === 'top' ? offsetData.bottom.y : 0;
      var leftDistance = basePlacement === 'right' ? offsetData.left.x : 0;
      var rightDistance = basePlacement === 'left' ? offsetData.right.x : 0;
      var exceedsTop = popperRect.top - clientY + topDistance > interactiveBorder;
      var exceedsBottom = clientY - popperRect.bottom - bottomDistance > interactiveBorder;
      var exceedsLeft = popperRect.left - clientX + leftDistance > interactiveBorder;
      var exceedsRight = clientX - popperRect.right - rightDistance > interactiveBorder;
      return exceedsTop || exceedsBottom || exceedsLeft || exceedsRight;
    });
  }
  function updateTransitionEndListener(box, action, listener) {
    var method = action + "EventListener";


    ['transitionend', 'webkitTransitionEnd'].forEach(function (event) {
      box[method](event, listener);
    });
  }


  function actualContains(parent, child) {
    var target = child;

    while (target) {
      var _target$getRootNode;

      if (parent.contains(target)) {
        return true;
      }

      target = target.getRootNode == null ? void 0 : (_target$getRootNode = target.getRootNode()) == null ? void 0 : _target$getRootNode.host;
    }

    return false;
  }

  var currentInput = {
    isTouch: false
  };
  var lastMouseMoveTime = 0;


  function onDocumentTouchStart() {
    if (currentInput.isTouch) {
      return;
    }

    currentInput.isTouch = true;

    if (window.performance) {
      document.addEventListener('mousemove', onDocumentMouseMove);
    }
  }


  function onDocumentMouseMove() {
    var now = performance.now();

    if (now - lastMouseMoveTime < 20) {
      currentInput.isTouch = false;
      document.removeEventListener('mousemove', onDocumentMouseMove);
    }

    lastMouseMoveTime = now;
  }


  function onWindowBlur() {
    var activeElement = document.activeElement;

    if (isReferenceElement(activeElement)) {
      var instance = activeElement._tippy;

      if (activeElement.blur && !instance.state.isVisible) {
        activeElement.blur();
      }
    }
  }
  function bindGlobalEventListeners() {
    document.addEventListener('touchstart', onDocumentTouchStart, TOUCH_OPTIONS);
    window.addEventListener('blur', onWindowBlur);
  }

  function createMemoryLeakWarning(method) {
    var txt = method === 'destroy' ? 'n already-' : ' ';
    return [method + "() was called on a" + txt + "destroyed instance. This is a no-op but", 'indicates a potential memory leak.'].join(' ');
  }
  function clean(value) {
    var spacesAndTabs = /[ \t]{2,}/g;
    var lineStartWithSpaces = /^[ \t]*/gm;
    return value.replace(spacesAndTabs, ' ').replace(lineStartWithSpaces, '').trim();
  }

  function getDevMessage(message) {
    return clean("\n  %ctippy.js\n\n  %c" + clean(message) + "\n\n  %c\uD83D\uDC77\u200D This is a development-only message. It will be removed in production.\n  ");
  }

  function getFormattedMessage(message) {
    return [getDevMessage(message),
    'color: #00C584; font-size: 1.3em; font-weight: bold;',
    'line-height: 1.5',
    'color: #a6a095;'];
  }

  var visitedMessages;

  {
    resetVisitedMessages();
  }

  function resetVisitedMessages() {
    visitedMessages = new Set();
  }
  function warnWhen(condition, message) {
    if (condition && !visitedMessages.has(message)) {
      var _console;

      visitedMessages.add(message);

      (_console = console).warn.apply(_console, getFormattedMessage(message));
    }
  }
  function errorWhen(condition, message) {
    if (condition && !visitedMessages.has(message)) {
      var _console2;

      visitedMessages.add(message);

      (_console2 = console).error.apply(_console2, getFormattedMessage(message));
    }
  }
  function validateTargets(targets) {
    var didPassFalsyValue = !targets;
    var didPassPlainObject = Object.prototype.toString.call(targets) === '[object Object]' && !targets.addEventListener;
    errorWhen(didPassFalsyValue, ['tippy() was passed', '`' + String(targets) + '`', 'as its targets (first) argument. Valid types are: String, Element,', 'Element[], or NodeList.'].join(' '));
    errorWhen(didPassPlainObject, ['tippy() was passed a plain object which is not supported as an argument', 'for virtual positioning. Use props.getReferenceClientRect instead.'].join(' '));
  }

  var pluginProps = {
    animateFill: false,
    followCursor: false,
    inlinePositioning: false,
    sticky: false
  };
  var renderProps = {
    allowHTML: false,
    animation: 'fade',
    arrow: true,
    content: '',
    inertia: false,
    maxWidth: 350,
    role: 'tooltip',
    theme: '',
    zIndex: 9999
  };
  var defaultProps = Object.assign({
    appendTo: TIPPY_DEFAULT_APPEND_TO,
    aria: {
      content: 'auto',
      expanded: 'auto'
    },
    delay: 0,
    duration: [300, 250],
    getReferenceClientRect: null,
    hideOnClick: true,
    ignoreAttributes: false,
    interactive: false,
    interactiveBorder: 2,
    interactiveDebounce: 0,
    moveTransition: '',
    offset: [0, 10],
    onAfterUpdate: function onAfterUpdate() {},
    onBeforeUpdate: function onBeforeUpdate() {},
    onCreate: function onCreate() {},
    onDestroy: function onDestroy() {},
    onHidden: function onHidden() {},
    onHide: function onHide() {},
    onMount: function onMount() {},
    onShow: function onShow() {},
    onShown: function onShown() {},
    onTrigger: function onTrigger() {},
    onUntrigger: function onUntrigger() {},
    onClickOutside: function onClickOutside() {},
    placement: 'top',
    plugins: [],
    popperOptions: {},
    render: null,
    showOnCreate: false,
    touch: true,
    trigger: 'mouseenter focus',
    triggerTarget: null
  }, pluginProps, renderProps);
  var defaultKeys = Object.keys(defaultProps);
  var setDefaultProps = function setDefaultProps(partialProps) {

    {
      validateProps(partialProps, []);
    }

    var keys = Object.keys(partialProps);
    keys.forEach(function (key) {
      defaultProps[key] = partialProps[key];
    });
  };
  function getExtendedPassedProps(passedProps) {
    var plugins = passedProps.plugins || [];
    var pluginProps = plugins.reduce(function (acc, plugin) {
      var name = plugin.name,
          defaultValue = plugin.defaultValue;

      if (name) {
        var _name;

        acc[name] = passedProps[name] !== undefined ? passedProps[name] : (_name = defaultProps[name]) != null ? _name : defaultValue;
      }

      return acc;
    }, {});
    return Object.assign({}, passedProps, pluginProps);
  }
  function getDataAttributeProps(reference, plugins) {
    var propKeys = plugins ? Object.keys(getExtendedPassedProps(Object.assign({}, defaultProps, {
      plugins: plugins
    }))) : defaultKeys;
    var props = propKeys.reduce(function (acc, key) {
      var valueAsString = (reference.getAttribute("data-tippy-" + key) || '').trim();

      if (!valueAsString) {
        return acc;
      }

      if (key === 'content') {
        acc[key] = valueAsString;
      } else {
        try {
          acc[key] = JSON.parse(valueAsString);
        } catch (e) {
          acc[key] = valueAsString;
        }
      }

      return acc;
    }, {});
    return props;
  }
  function evaluateProps(reference, props) {
    var out = Object.assign({}, props, {
      content: invokeWithArgsOrReturn(props.content, [reference])
    }, props.ignoreAttributes ? {} : getDataAttributeProps(reference, props.plugins));
    out.aria = Object.assign({}, defaultProps.aria, out.aria);
    out.aria = {
      expanded: out.aria.expanded === 'auto' ? props.interactive : out.aria.expanded,
      content: out.aria.content === 'auto' ? props.interactive ? null : 'describedby' : out.aria.content
    };
    return out;
  }
  function validateProps(partialProps, plugins) {
    if (partialProps === void 0) {
      partialProps = {};
    }

    if (plugins === void 0) {
      plugins = [];
    }

    var keys = Object.keys(partialProps);
    keys.forEach(function (prop) {
      var nonPluginProps = removeProperties(defaultProps, Object.keys(pluginProps));
      var didPassUnknownProp = !hasOwnProperty(nonPluginProps, prop);

      if (didPassUnknownProp) {
        didPassUnknownProp = plugins.filter(function (plugin) {
          return plugin.name === prop;
        }).length === 0;
      }

      warnWhen(didPassUnknownProp, ["`" + prop + "`", "is not a valid prop. You may have spelled it incorrectly, or if it's", 'a plugin, forgot to pass it in an array as props.plugins.', '\n\n', 'All props: https://atomiks.github.io/tippyjs/v6/all-props/\n', 'Plugins: https://atomiks.github.io/tippyjs/v6/plugins/'].join(' '));
    });
  }

  var innerHTML = function innerHTML() {
    return 'innerHTML';
  };

  function dangerouslySetInnerHTML(element, html) {
    element[innerHTML()] = html;
  }

  function createArrowElement(value) {
    var arrow = div();

    if (value === true) {
      arrow.className = ARROW_CLASS;
    } else {
      arrow.className = SVG_ARROW_CLASS;

      if (isElement(value)) {
        arrow.appendChild(value);
      } else {
        dangerouslySetInnerHTML(arrow, value);
      }
    }

    return arrow;
  }

  function setContent(content, props) {
    if (isElement(props.content)) {
      dangerouslySetInnerHTML(content, '');
      content.appendChild(props.content);
    } else if (typeof props.content !== 'function') {
      if (props.allowHTML) {
        dangerouslySetInnerHTML(content, props.content);
      } else {
        content.textContent = props.content;
      }
    }
  }
  function getChildren(popper) {
    var box = popper.firstElementChild;
    var boxChildren = arrayFrom(box.children);
    return {
      box: box,
      content: boxChildren.find(function (node) {
        return node.classList.contains(CONTENT_CLASS);
      }),
      arrow: boxChildren.find(function (node) {
        return node.classList.contains(ARROW_CLASS) || node.classList.contains(SVG_ARROW_CLASS);
      }),
      backdrop: boxChildren.find(function (node) {
        return node.classList.contains(BACKDROP_CLASS);
      })
    };
  }
  function render(instance) {
    var popper = div();
    var box = div();
    box.className = BOX_CLASS;
    box.setAttribute('data-state', 'hidden');
    box.setAttribute('tabindex', '-1');
    var content = div();
    content.className = CONTENT_CLASS;
    content.setAttribute('data-state', 'hidden');
    setContent(content, instance.props);
    popper.appendChild(box);
    box.appendChild(content);
    onUpdate(instance.props, instance.props);

    function onUpdate(prevProps, nextProps) {
      var _getChildren = getChildren(popper),
          box = _getChildren.box,
          content = _getChildren.content,
          arrow = _getChildren.arrow;

      if (nextProps.theme) {
        box.setAttribute('data-theme', nextProps.theme);
      } else {
        box.removeAttribute('data-theme');
      }

      if (typeof nextProps.animation === 'string') {
        box.setAttribute('data-animation', nextProps.animation);
      } else {
        box.removeAttribute('data-animation');
      }

      if (nextProps.inertia) {
        box.setAttribute('data-inertia', '');
      } else {
        box.removeAttribute('data-inertia');
      }

      box.style.maxWidth = typeof nextProps.maxWidth === 'number' ? nextProps.maxWidth + "px" : nextProps.maxWidth;

      if (nextProps.role) {
        box.setAttribute('role', nextProps.role);
      } else {
        box.removeAttribute('role');
      }

      if (prevProps.content !== nextProps.content || prevProps.allowHTML !== nextProps.allowHTML) {
        setContent(content, instance.props);
      }

      if (nextProps.arrow) {
        if (!arrow) {
          box.appendChild(createArrowElement(nextProps.arrow));
        } else if (prevProps.arrow !== nextProps.arrow) {
          box.removeChild(arrow);
          box.appendChild(createArrowElement(nextProps.arrow));
        }
      } else if (arrow) {
        box.removeChild(arrow);
      }
    }

    return {
      popper: popper,
      onUpdate: onUpdate
    };
  }


  render.$$tippy = true;

  var idCounter = 1;
  var mouseMoveListeners = [];

  var mountedInstances = [];
  function createTippy(reference, passedProps) {
    var props = evaluateProps(reference, Object.assign({}, defaultProps, getExtendedPassedProps(removeUndefinedProps(passedProps))));



    var showTimeout;
    var hideTimeout;
    var scheduleHideAnimationFrame;
    var isVisibleFromClick = false;
    var didHideDueToDocumentMouseDown = false;
    var didTouchMove = false;
    var ignoreOnFirstUpdate = false;
    var lastTriggerEvent;
    var currentTransitionEndListener;
    var onFirstUpdate;
    var listeners = [];
    var debouncedOnMouseMove = debounce(onMouseMove, props.interactiveDebounce);
    var currentTarget;



    var id = idCounter++;
    var popperInstance = null;
    var plugins = unique(props.plugins);
    var state = {

      isEnabled: true,

      isVisible: false,

      isDestroyed: false,

      isMounted: false,

      isShown: false
    };
    var instance = {

      id: id,
      reference: reference,
      popper: div(),
      popperInstance: popperInstance,
      props: props,
      state: state,
      plugins: plugins,

      clearDelayTimeouts: clearDelayTimeouts,
      setProps: setProps,
      setContent: setContent,
      show: show,
      hide: hide,
      hideWithInteractivity: hideWithInteractivity,
      enable: enable,
      disable: disable,
      unmount: unmount,
      destroy: destroy
    };




    if (!props.render) {
      {
        errorWhen(true, 'render() function has not been supplied.');
      }

      return instance;
    }




    var _props$render = props.render(instance),
        popper = _props$render.popper,
        onUpdate = _props$render.onUpdate;

    popper.setAttribute('data-tippy-root', '');
    popper.id = "tippy-" + instance.id;
    instance.popper = popper;
    reference._tippy = instance;
    popper._tippy = instance;
    var pluginsHooks = plugins.map(function (plugin) {
      return plugin.fn(instance);
    });
    var hasAriaExpanded = reference.hasAttribute('aria-expanded');
    addListeners();
    handleAriaExpandedAttribute();
    handleStyles();
    invokeHook('onCreate', [instance]);

    if (props.showOnCreate) {
      scheduleShow();
    }



    popper.addEventListener('mouseenter', function () {
      if (instance.props.interactive && instance.state.isVisible) {
        instance.clearDelayTimeouts();
      }
    });
    popper.addEventListener('mouseleave', function () {
      if (instance.props.interactive && instance.props.trigger.indexOf('mouseenter') >= 0) {
        getDocument().addEventListener('mousemove', debouncedOnMouseMove);
      }
    });
    return instance;



    function getNormalizedTouchSettings() {
      var touch = instance.props.touch;
      return Array.isArray(touch) ? touch : [touch, 0];
    }

    function getIsCustomTouchBehavior() {
      return getNormalizedTouchSettings()[0] === 'hold';
    }

    function getIsDefaultRenderFn() {
      var _instance$props$rende;


      return !!((_instance$props$rende = instance.props.render) != null && _instance$props$rende.$$tippy);
    }

    function getCurrentTarget() {
      return currentTarget || reference;
    }

    function getDocument() {
      var parent = getCurrentTarget().parentNode;
      return parent ? getOwnerDocument(parent) : document;
    }

    function getDefaultTemplateChildren() {
      return getChildren(popper);
    }

    function getDelay(isShow) {



      if (instance.state.isMounted && !instance.state.isVisible || currentInput.isTouch || lastTriggerEvent && lastTriggerEvent.type === 'focus') {
        return 0;
      }

      return getValueAtIndexOrReturn(instance.props.delay, isShow ? 0 : 1, defaultProps.delay);
    }

    function handleStyles(fromHide) {
      if (fromHide === void 0) {
        fromHide = false;
      }

      popper.style.pointerEvents = instance.props.interactive && !fromHide ? '' : 'none';
      popper.style.zIndex = "" + instance.props.zIndex;
    }

    function invokeHook(hook, args, shouldInvokePropsHook) {
      if (shouldInvokePropsHook === void 0) {
        shouldInvokePropsHook = true;
      }

      pluginsHooks.forEach(function (pluginHooks) {
        if (pluginHooks[hook]) {
          pluginHooks[hook].apply(pluginHooks, args);
        }
      });

      if (shouldInvokePropsHook) {
        var _instance$props;

        (_instance$props = instance.props)[hook].apply(_instance$props, args);
      }
    }

    function handleAriaContentAttribute() {
      var aria = instance.props.aria;

      if (!aria.content) {
        return;
      }

      var attr = "aria-" + aria.content;
      var id = popper.id;
      var nodes = normalizeToArray(instance.props.triggerTarget || reference);
      nodes.forEach(function (node) {
        var currentValue = node.getAttribute(attr);

        if (instance.state.isVisible) {
          node.setAttribute(attr, currentValue ? currentValue + " " + id : id);
        } else {
          var nextValue = currentValue && currentValue.replace(id, '').trim();

          if (nextValue) {
            node.setAttribute(attr, nextValue);
          } else {
            node.removeAttribute(attr);
          }
        }
      });
    }

    function handleAriaExpandedAttribute() {
      if (hasAriaExpanded || !instance.props.aria.expanded) {
        return;
      }

      var nodes = normalizeToArray(instance.props.triggerTarget || reference);
      nodes.forEach(function (node) {
        if (instance.props.interactive) {
          node.setAttribute('aria-expanded', instance.state.isVisible && node === getCurrentTarget() ? 'true' : 'false');
        } else {
          node.removeAttribute('aria-expanded');
        }
      });
    }

    function cleanupInteractiveMouseListeners() {
      getDocument().removeEventListener('mousemove', debouncedOnMouseMove);
      mouseMoveListeners = mouseMoveListeners.filter(function (listener) {
        return listener !== debouncedOnMouseMove;
      });
    }

    function onDocumentPress(event) {

      if (currentInput.isTouch) {
        if (didTouchMove || event.type === 'mousedown') {
          return;
        }
      }

      var actualTarget = event.composedPath && event.composedPath()[0] || event.target;

      if (instance.props.interactive && actualContains(popper, actualTarget)) {
        return;
      }


      if (normalizeToArray(instance.props.triggerTarget || reference).some(function (el) {
        return actualContains(el, actualTarget);
      })) {
        if (currentInput.isTouch) {
          return;
        }

        if (instance.state.isVisible && instance.props.trigger.indexOf('click') >= 0) {
          return;
        }
      } else {
        invokeHook('onClickOutside', [instance, event]);
      }

      if (instance.props.hideOnClick === true) {
        instance.clearDelayTimeouts();
        instance.hide();



        didHideDueToDocumentMouseDown = true;
        setTimeout(function () {
          didHideDueToDocumentMouseDown = false;
        });



        if (!instance.state.isMounted) {
          removeDocumentPress();
        }
      }
    }

    function onTouchMove() {
      didTouchMove = true;
    }

    function onTouchStart() {
      didTouchMove = false;
    }

    function addDocumentPress() {
      var doc = getDocument();
      doc.addEventListener('mousedown', onDocumentPress, true);
      doc.addEventListener('touchend', onDocumentPress, TOUCH_OPTIONS);
      doc.addEventListener('touchstart', onTouchStart, TOUCH_OPTIONS);
      doc.addEventListener('touchmove', onTouchMove, TOUCH_OPTIONS);
    }

    function removeDocumentPress() {
      var doc = getDocument();
      doc.removeEventListener('mousedown', onDocumentPress, true);
      doc.removeEventListener('touchend', onDocumentPress, TOUCH_OPTIONS);
      doc.removeEventListener('touchstart', onTouchStart, TOUCH_OPTIONS);
      doc.removeEventListener('touchmove', onTouchMove, TOUCH_OPTIONS);
    }

    function onTransitionedOut(duration, callback) {
      onTransitionEnd(duration, function () {
        if (!instance.state.isVisible && popper.parentNode && popper.parentNode.contains(popper)) {
          callback();
        }
      });
    }

    function onTransitionedIn(duration, callback) {
      onTransitionEnd(duration, callback);
    }

    function onTransitionEnd(duration, callback) {
      var box = getDefaultTemplateChildren().box;

      function listener(event) {
        if (event.target === box) {
          updateTransitionEndListener(box, 'remove', listener);
          callback();
        }
      }



      if (duration === 0) {
        return callback();
      }

      updateTransitionEndListener(box, 'remove', currentTransitionEndListener);
      updateTransitionEndListener(box, 'add', listener);
      currentTransitionEndListener = listener;
    }

    function on(eventType, handler, options) {
      if (options === void 0) {
        options = false;
      }

      var nodes = normalizeToArray(instance.props.triggerTarget || reference);
      nodes.forEach(function (node) {
        node.addEventListener(eventType, handler, options);
        listeners.push({
          node: node,
          eventType: eventType,
          handler: handler,
          options: options
        });
      });
    }

    function addListeners() {
      if (getIsCustomTouchBehavior()) {
        on('touchstart', onTrigger, {
          passive: true
        });
        on('touchend', onMouseLeave, {
          passive: true
        });
      }

      splitBySpaces(instance.props.trigger).forEach(function (eventType) {
        if (eventType === 'manual') {
          return;
        }

        on(eventType, onTrigger);

        switch (eventType) {
          case 'mouseenter':
            on('mouseleave', onMouseLeave);
            break;

          case 'focus':
            on(isIE11 ? 'focusout' : 'blur', onBlurOrFocusOut);
            break;

          case 'focusin':
            on('focusout', onBlurOrFocusOut);
            break;
        }
      });
    }

    function removeListeners() {
      listeners.forEach(function (_ref) {
        var node = _ref.node,
            eventType = _ref.eventType,
            handler = _ref.handler,
            options = _ref.options;
        node.removeEventListener(eventType, handler, options);
      });
      listeners = [];
    }

    function onTrigger(event) {
      var _lastTriggerEvent;

      var shouldScheduleClickHide = false;

      if (!instance.state.isEnabled || isEventListenerStopped(event) || didHideDueToDocumentMouseDown) {
        return;
      }

      var wasFocused = ((_lastTriggerEvent = lastTriggerEvent) == null ? void 0 : _lastTriggerEvent.type) === 'focus';
      lastTriggerEvent = event;
      currentTarget = event.currentTarget;
      handleAriaExpandedAttribute();

      if (!instance.state.isVisible && isMouseEvent(event)) {




        mouseMoveListeners.forEach(function (listener) {
          return listener(event);
        });
      }


      if (event.type === 'click' && (instance.props.trigger.indexOf('mouseenter') < 0 || isVisibleFromClick) && instance.props.hideOnClick !== false && instance.state.isVisible) {
        shouldScheduleClickHide = true;
      } else {
        scheduleShow(event);
      }

      if (event.type === 'click') {
        isVisibleFromClick = !shouldScheduleClickHide;
      }

      if (shouldScheduleClickHide && !wasFocused) {
        scheduleHide(event);
      }
    }

    function onMouseMove(event) {
      var target = event.target;
      var isCursorOverReferenceOrPopper = getCurrentTarget().contains(target) || popper.contains(target);

      if (event.type === 'mousemove' && isCursorOverReferenceOrPopper) {
        return;
      }

      var popperTreeData = getNestedPopperTree().concat(popper).map(function (popper) {
        var _instance$popperInsta;

        var instance = popper._tippy;
        var state = (_instance$popperInsta = instance.popperInstance) == null ? void 0 : _instance$popperInsta.state;

        if (state) {
          return {
            popperRect: popper.getBoundingClientRect(),
            popperState: state,
            props: props
          };
        }

        return null;
      }).filter(Boolean);

      if (isCursorOutsideInteractiveBorder(popperTreeData, event)) {
        cleanupInteractiveMouseListeners();
        scheduleHide(event);
      }
    }

    function onMouseLeave(event) {
      var shouldBail = isEventListenerStopped(event) || instance.props.trigger.indexOf('click') >= 0 && isVisibleFromClick;

      if (shouldBail) {
        return;
      }

      if (instance.props.interactive) {
        instance.hideWithInteractivity(event);
        return;
      }

      scheduleHide(event);
    }

    function onBlurOrFocusOut(event) {
      if (instance.props.trigger.indexOf('focusin') < 0 && event.target !== getCurrentTarget()) {
        return;
      }


      if (instance.props.interactive && event.relatedTarget && popper.contains(event.relatedTarget)) {
        return;
      }

      scheduleHide(event);
    }

    function isEventListenerStopped(event) {
      return currentInput.isTouch ? getIsCustomTouchBehavior() !== event.type.indexOf('touch') >= 0 : false;
    }

    function createPopperInstance() {
      destroyPopperInstance();
      var _instance$props2 = instance.props,
          popperOptions = _instance$props2.popperOptions,
          placement = _instance$props2.placement,
          offset = _instance$props2.offset,
          getReferenceClientRect = _instance$props2.getReferenceClientRect,
          moveTransition = _instance$props2.moveTransition;
      var arrow = getIsDefaultRenderFn() ? getChildren(popper).arrow : null;
      var computedReference = getReferenceClientRect ? {
        getBoundingClientRect: getReferenceClientRect,
        contextElement: getReferenceClientRect.contextElement || getCurrentTarget()
      } : reference;
      var tippyModifier = {
        name: '$$tippy',
        enabled: true,
        phase: 'beforeWrite',
        requires: ['computeStyles'],
        fn: function fn(_ref2) {
          var state = _ref2.state;

          if (getIsDefaultRenderFn()) {
            var _getDefaultTemplateCh = getDefaultTemplateChildren(),
                box = _getDefaultTemplateCh.box;

            ['placement', 'reference-hidden', 'escaped'].forEach(function (attr) {
              if (attr === 'placement') {
                box.setAttribute('data-placement', state.placement);
              } else {
                if (state.attributes.popper["data-popper-" + attr]) {
                  box.setAttribute("data-" + attr, '');
                } else {
                  box.removeAttribute("data-" + attr);
                }
              }
            });
            state.attributes.popper = {};
          }
        }
      };
      var modifiers = [{
        name: 'offset',
        options: {
          offset: offset
        }
      }, {
        name: 'preventOverflow',
        options: {
          padding: {
            top: 2,
            bottom: 2,
            left: 5,
            right: 5
          }
        }
      }, {
        name: 'flip',
        options: {
          padding: 5
        }
      }, {
        name: 'computeStyles',
        options: {
          adaptive: !moveTransition
        }
      }, tippyModifier];

      if (getIsDefaultRenderFn() && arrow) {
        modifiers.push({
          name: 'arrow',
          options: {
            element: arrow,
            padding: 3
          }
        });
      }

      modifiers.push.apply(modifiers, (popperOptions == null ? void 0 : popperOptions.modifiers) || []);
      instance.popperInstance = core.createPopper(computedReference, popper, Object.assign({}, popperOptions, {
        placement: placement,
        onFirstUpdate: onFirstUpdate,
        modifiers: modifiers
      }));
    }

    function destroyPopperInstance() {
      if (instance.popperInstance) {
        instance.popperInstance.destroy();
        instance.popperInstance = null;
      }
    }

    function mount() {
      var appendTo = instance.props.appendTo;
      var parentNode;





      var node = getCurrentTarget();

      if (instance.props.interactive && appendTo === TIPPY_DEFAULT_APPEND_TO || appendTo === 'parent') {
        parentNode = node.parentNode;
      } else {
        parentNode = invokeWithArgsOrReturn(appendTo, [node]);
      }



      if (!parentNode.contains(popper)) {
        parentNode.appendChild(popper);
      }

      instance.state.isMounted = true;
      createPopperInstance();


      {

        warnWhen(instance.props.interactive && appendTo === defaultProps.appendTo && node.nextElementSibling !== popper, ['Interactive tippy element may not be accessible via keyboard', 'navigation because it is not directly after the reference element', 'in the DOM source order.', '\n\n', 'Using a wrapper <div> or <span> tag around the reference element', 'solves this by creating a new parentNode context.', '\n\n', 'Specifying `appendTo: document.body` silences this warning, but it', 'assumes you are using a focus management solution to handle', 'keyboard navigation.', '\n\n', 'See: https://atomiks.github.io/tippyjs/v6/accessibility/#interactivity'].join(' '));
      }
    }

    function getNestedPopperTree() {
      return arrayFrom(popper.querySelectorAll('[data-tippy-root]'));
    }

    function scheduleShow(event) {
      instance.clearDelayTimeouts();

      if (event) {
        invokeHook('onTrigger', [instance, event]);
      }

      addDocumentPress();
      var delay = getDelay(true);

      var _getNormalizedTouchSe = getNormalizedTouchSettings(),
          touchValue = _getNormalizedTouchSe[0],
          touchDelay = _getNormalizedTouchSe[1];

      if (currentInput.isTouch && touchValue === 'hold' && touchDelay) {
        delay = touchDelay;
      }

      if (delay) {
        showTimeout = setTimeout(function () {
          instance.show();
        }, delay);
      } else {
        instance.show();
      }
    }

    function scheduleHide(event) {
      instance.clearDelayTimeouts();
      invokeHook('onUntrigger', [instance, event]);

      if (!instance.state.isVisible) {
        removeDocumentPress();
        return;
      }





      if (instance.props.trigger.indexOf('mouseenter') >= 0 && instance.props.trigger.indexOf('click') >= 0 && ['mouseleave', 'mousemove'].indexOf(event.type) >= 0 && isVisibleFromClick) {
        return;
      }

      var delay = getDelay(false);

      if (delay) {
        hideTimeout = setTimeout(function () {
          if (instance.state.isVisible) {
            instance.hide();
          }
        }, delay);
      } else {


        scheduleHideAnimationFrame = requestAnimationFrame(function () {
          instance.hide();
        });
      }
    }




    function enable() {
      instance.state.isEnabled = true;
    }

    function disable() {


      instance.hide();
      instance.state.isEnabled = false;
    }

    function clearDelayTimeouts() {
      clearTimeout(showTimeout);
      clearTimeout(hideTimeout);
      cancelAnimationFrame(scheduleHideAnimationFrame);
    }

    function setProps(partialProps) {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('setProps'));
      }

      if (instance.state.isDestroyed) {
        return;
      }

      invokeHook('onBeforeUpdate', [instance, partialProps]);
      removeListeners();
      var prevProps = instance.props;
      var nextProps = evaluateProps(reference, Object.assign({}, prevProps, removeUndefinedProps(partialProps), {
        ignoreAttributes: true
      }));
      instance.props = nextProps;
      addListeners();

      if (prevProps.interactiveDebounce !== nextProps.interactiveDebounce) {
        cleanupInteractiveMouseListeners();
        debouncedOnMouseMove = debounce(onMouseMove, nextProps.interactiveDebounce);
      }


      if (prevProps.triggerTarget && !nextProps.triggerTarget) {
        normalizeToArray(prevProps.triggerTarget).forEach(function (node) {
          node.removeAttribute('aria-expanded');
        });
      } else if (nextProps.triggerTarget) {
        reference.removeAttribute('aria-expanded');
      }

      handleAriaExpandedAttribute();
      handleStyles();

      if (onUpdate) {
        onUpdate(prevProps, nextProps);
      }

      if (instance.popperInstance) {
        createPopperInstance();




        getNestedPopperTree().forEach(function (nestedPopper) {


          requestAnimationFrame(nestedPopper._tippy.popperInstance.forceUpdate);
        });
      }

      invokeHook('onAfterUpdate', [instance, partialProps]);
    }

    function setContent(content) {
      instance.setProps({
        content: content
      });
    }

    function show() {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('show'));
      }


      var isAlreadyVisible = instance.state.isVisible;
      var isDestroyed = instance.state.isDestroyed;
      var isDisabled = !instance.state.isEnabled;
      var isTouchAndTouchDisabled = currentInput.isTouch && !instance.props.touch;
      var duration = getValueAtIndexOrReturn(instance.props.duration, 0, defaultProps.duration);

      if (isAlreadyVisible || isDestroyed || isDisabled || isTouchAndTouchDisabled) {
        return;
      }




      if (getCurrentTarget().hasAttribute('disabled')) {
        return;
      }

      invokeHook('onShow', [instance], false);

      if (instance.props.onShow(instance) === false) {
        return;
      }

      instance.state.isVisible = true;

      if (getIsDefaultRenderFn()) {
        popper.style.visibility = 'visible';
      }

      handleStyles();
      addDocumentPress();

      if (!instance.state.isMounted) {
        popper.style.transition = 'none';
      }



      if (getIsDefaultRenderFn()) {
        var _getDefaultTemplateCh2 = getDefaultTemplateChildren(),
            box = _getDefaultTemplateCh2.box,
            content = _getDefaultTemplateCh2.content;

        setTransitionDuration([box, content], 0);
      }

      onFirstUpdate = function onFirstUpdate() {
        var _instance$popperInsta2;

        if (!instance.state.isVisible || ignoreOnFirstUpdate) {
          return;
        }

        ignoreOnFirstUpdate = true;

        void popper.offsetHeight;
        popper.style.transition = instance.props.moveTransition;

        if (getIsDefaultRenderFn() && instance.props.animation) {
          var _getDefaultTemplateCh3 = getDefaultTemplateChildren(),
              _box = _getDefaultTemplateCh3.box,
              _content = _getDefaultTemplateCh3.content;

          setTransitionDuration([_box, _content], duration);
          setVisibilityState([_box, _content], 'visible');
        }

        handleAriaContentAttribute();
        handleAriaExpandedAttribute();
        pushIfUnique(mountedInstances, instance);


        (_instance$popperInsta2 = instance.popperInstance) == null ? void 0 : _instance$popperInsta2.forceUpdate();
        invokeHook('onMount', [instance]);

        if (instance.props.animation && getIsDefaultRenderFn()) {
          onTransitionedIn(duration, function () {
            instance.state.isShown = true;
            invokeHook('onShown', [instance]);
          });
        }
      };

      mount();
    }

    function hide() {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('hide'));
      }


      var isAlreadyHidden = !instance.state.isVisible;
      var isDestroyed = instance.state.isDestroyed;
      var isDisabled = !instance.state.isEnabled;
      var duration = getValueAtIndexOrReturn(instance.props.duration, 1, defaultProps.duration);

      if (isAlreadyHidden || isDestroyed || isDisabled) {
        return;
      }

      invokeHook('onHide', [instance], false);

      if (instance.props.onHide(instance) === false) {
        return;
      }

      instance.state.isVisible = false;
      instance.state.isShown = false;
      ignoreOnFirstUpdate = false;
      isVisibleFromClick = false;

      if (getIsDefaultRenderFn()) {
        popper.style.visibility = 'hidden';
      }

      cleanupInteractiveMouseListeners();
      removeDocumentPress();
      handleStyles(true);

      if (getIsDefaultRenderFn()) {
        var _getDefaultTemplateCh4 = getDefaultTemplateChildren(),
            box = _getDefaultTemplateCh4.box,
            content = _getDefaultTemplateCh4.content;

        if (instance.props.animation) {
          setTransitionDuration([box, content], duration);
          setVisibilityState([box, content], 'hidden');
        }
      }

      handleAriaContentAttribute();
      handleAriaExpandedAttribute();

      if (instance.props.animation) {
        if (getIsDefaultRenderFn()) {
          onTransitionedOut(duration, instance.unmount);
        }
      } else {
        instance.unmount();
      }
    }

    function hideWithInteractivity(event) {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('hideWithInteractivity'));
      }

      getDocument().addEventListener('mousemove', debouncedOnMouseMove);
      pushIfUnique(mouseMoveListeners, debouncedOnMouseMove);
      debouncedOnMouseMove(event);
    }

    function unmount() {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('unmount'));
      }

      if (instance.state.isVisible) {
        instance.hide();
      }

      if (!instance.state.isMounted) {
        return;
      }

      destroyPopperInstance();



      getNestedPopperTree().forEach(function (nestedPopper) {
        nestedPopper._tippy.unmount();
      });

      if (popper.parentNode) {
        popper.parentNode.removeChild(popper);
      }

      mountedInstances = mountedInstances.filter(function (i) {
        return i !== instance;
      });
      instance.state.isMounted = false;
      invokeHook('onHidden', [instance]);
    }

    function destroy() {

      {
        warnWhen(instance.state.isDestroyed, createMemoryLeakWarning('destroy'));
      }

      if (instance.state.isDestroyed) {
        return;
      }

      instance.clearDelayTimeouts();
      instance.unmount();
      removeListeners();
      delete reference._tippy;
      instance.state.isDestroyed = true;
      invokeHook('onDestroy', [instance]);
    }
  }

  function tippy(targets, optionalProps) {
    if (optionalProps === void 0) {
      optionalProps = {};
    }

    var plugins = defaultProps.plugins.concat(optionalProps.plugins || []);


    {
      validateTargets(targets);
      validateProps(optionalProps, plugins);
    }

    bindGlobalEventListeners();
    var passedProps = Object.assign({}, optionalProps, {
      plugins: plugins
    });
    var elements = getArrayOfElements(targets);


    {
      var isSingleContentElement = isElement(passedProps.content);
      var isMoreThanOneReferenceElement = elements.length > 1;
      warnWhen(isSingleContentElement && isMoreThanOneReferenceElement, ['tippy() was passed an Element as the `content` prop, but more than', 'one tippy instance was created by this invocation. This means the', 'content element will only be appended to the last tippy instance.', '\n\n', 'Instead, pass the .innerHTML of the element, or use a function that', 'returns a cloned version of the element instead.', '\n\n', '1) content: element.innerHTML\n', '2) content: () => element.cloneNode(true)'].join(' '));
    }

    var instances = elements.reduce(function (acc, reference) {
      var instance = reference && createTippy(reference, passedProps);

      if (instance) {
        acc.push(instance);
      }

      return acc;
    }, []);
    return isElement(targets) ? instances[0] : instances;
  }

  tippy.defaultProps = defaultProps;
  tippy.setDefaultProps = setDefaultProps;
  tippy.currentInput = currentInput;
  var hideAll = function hideAll(_temp) {
    var _ref = _temp === void 0 ? {} : _temp,
        excludedReferenceOrInstance = _ref.exclude,
        duration = _ref.duration;

    mountedInstances.forEach(function (instance) {
      var isExcluded = false;

      if (excludedReferenceOrInstance) {
        isExcluded = isReferenceElement(excludedReferenceOrInstance) ? instance.reference === excludedReferenceOrInstance : instance.popper === excludedReferenceOrInstance.popper;
      }

      if (!isExcluded) {
        var originalDuration = instance.props.duration;
        instance.setProps({
          duration: duration
        });
        instance.hide();

        if (!instance.state.isDestroyed) {
          instance.setProps({
            duration: originalDuration
          });
        }
      }
    });
  };





  var applyStylesModifier = Object.assign({}, core.applyStyles, {
    effect: function effect(_ref) {
      var state = _ref.state;
      var initialStyles = {
        popper: {
          position: state.options.strategy,
          left: '0',
          top: '0',
          margin: '0'
        },
        arrow: {
          position: 'absolute'
        },
        reference: {}
      };
      Object.assign(state.elements.popper.style, initialStyles.popper);
      state.styles = initialStyles;

      if (state.elements.arrow) {
        Object.assign(state.elements.arrow.style, initialStyles.arrow);
      }


    }
  });

  var createSingleton = function createSingleton(tippyInstances, optionalProps) {
    var _optionalProps$popper;

    if (optionalProps === void 0) {
      optionalProps = {};
    }


    {
      errorWhen(!Array.isArray(tippyInstances), ['The first argument passed to createSingleton() must be an array of', 'tippy instances. The passed value was', String(tippyInstances)].join(' '));
    }

    var individualInstances = tippyInstances;
    var references = [];
    var triggerTargets = [];
    var currentTarget;
    var overrides = optionalProps.overrides;
    var interceptSetPropsCleanups = [];
    var shownOnCreate = false;

    function setTriggerTargets() {
      triggerTargets = individualInstances.map(function (instance) {
        return normalizeToArray(instance.props.triggerTarget || instance.reference);
      }).reduce(function (acc, item) {
        return acc.concat(item);
      }, []);
    }

    function setReferences() {
      references = individualInstances.map(function (instance) {
        return instance.reference;
      });
    }

    function enableInstances(isEnabled) {
      individualInstances.forEach(function (instance) {
        if (isEnabled) {
          instance.enable();
        } else {
          instance.disable();
        }
      });
    }

    function interceptSetProps(singleton) {
      return individualInstances.map(function (instance) {
        var originalSetProps = instance.setProps;

        instance.setProps = function (props) {
          originalSetProps(props);

          if (instance.reference === currentTarget) {
            singleton.setProps(props);
          }
        };

        return function () {
          instance.setProps = originalSetProps;
        };
      });
    }


    function prepareInstance(singleton, target) {
      var index = triggerTargets.indexOf(target);

      if (target === currentTarget) {
        return;
      }

      currentTarget = target;
      var overrideProps = (overrides || []).concat('content').reduce(function (acc, prop) {
        acc[prop] = individualInstances[index].props[prop];
        return acc;
      }, {});
      singleton.setProps(Object.assign({}, overrideProps, {
        getReferenceClientRect: typeof overrideProps.getReferenceClientRect === 'function' ? overrideProps.getReferenceClientRect : function () {
          var _references$index;

          return (_references$index = references[index]) == null ? void 0 : _references$index.getBoundingClientRect();
        }
      }));
    }

    enableInstances(false);
    setReferences();
    setTriggerTargets();
    var plugin = {
      fn: function fn() {
        return {
          onDestroy: function onDestroy() {
            enableInstances(true);
          },
          onHidden: function onHidden() {
            currentTarget = null;
          },
          onClickOutside: function onClickOutside(instance) {
            if (instance.props.showOnCreate && !shownOnCreate) {
              shownOnCreate = true;
              currentTarget = null;
            }
          },
          onShow: function onShow(instance) {
            if (instance.props.showOnCreate && !shownOnCreate) {
              shownOnCreate = true;
              prepareInstance(instance, references[0]);
            }
          },
          onTrigger: function onTrigger(instance, event) {
            prepareInstance(instance, event.currentTarget);
          }
        };
      }
    };
    var singleton = tippy(div(), Object.assign({}, removeProperties(optionalProps, ['overrides']), {
      plugins: [plugin].concat(optionalProps.plugins || []),
      triggerTarget: triggerTargets,
      popperOptions: Object.assign({}, optionalProps.popperOptions, {
        modifiers: [].concat(((_optionalProps$popper = optionalProps.popperOptions) == null ? void 0 : _optionalProps$popper.modifiers) || [], [applyStylesModifier])
      })
    }));
    var originalShow = singleton.show;

    singleton.show = function (target) {
      originalShow();


      if (!currentTarget && target == null) {
        return prepareInstance(singleton, references[0]);
      }



      if (currentTarget && target == null) {
        return;
      }


      if (typeof target === 'number') {
        return references[target] && prepareInstance(singleton, references[target]);
      }


      if (individualInstances.indexOf(target) >= 0) {
        var ref = target.reference;
        return prepareInstance(singleton, ref);
      }


      if (references.indexOf(target) >= 0) {
        return prepareInstance(singleton, target);
      }
    };

    singleton.showNext = function () {
      var first = references[0];

      if (!currentTarget) {
        return singleton.show(0);
      }

      var index = references.indexOf(currentTarget);
      singleton.show(references[index + 1] || first);
    };

    singleton.showPrevious = function () {
      var last = references[references.length - 1];

      if (!currentTarget) {
        return singleton.show(last);
      }

      var index = references.indexOf(currentTarget);
      var target = references[index - 1] || last;
      singleton.show(target);
    };

    var originalSetProps = singleton.setProps;

    singleton.setProps = function (props) {
      overrides = props.overrides || overrides;
      originalSetProps(props);
    };

    singleton.setInstances = function (nextInstances) {
      enableInstances(true);
      interceptSetPropsCleanups.forEach(function (fn) {
        return fn();
      });
      individualInstances = nextInstances;
      enableInstances(false);
      setReferences();
      setTriggerTargets();
      interceptSetPropsCleanups = interceptSetProps(singleton);
      singleton.setProps({
        triggerTarget: triggerTargets
      });
    };

    interceptSetPropsCleanups = interceptSetProps(singleton);
    return singleton;
  };

  var BUBBLING_EVENTS_MAP = {
    mouseover: 'mouseenter',
    focusin: 'focus',
    click: 'click'
  };


  function delegate(targets, props) {

    {
      errorWhen(!(props && props.target), ['You must specity a `target` prop indicating a CSS selector string matching', 'the target elements that should receive a tippy.'].join(' '));
    }

    var listeners = [];
    var childTippyInstances = [];
    var disabled = false;
    var target = props.target;
    var nativeProps = removeProperties(props, ['target']);
    var parentProps = Object.assign({}, nativeProps, {
      trigger: 'manual',
      touch: false
    });
    var childProps = Object.assign({
      touch: defaultProps.touch
    }, nativeProps, {
      showOnCreate: true
    });
    var returnValue = tippy(targets, parentProps);
    var normalizedReturnValue = normalizeToArray(returnValue);

    function onTrigger(event) {
      if (!event.target || disabled) {
        return;
      }

      var targetNode = event.target.closest(target);

      if (!targetNode) {
        return;
      }





      var trigger = targetNode.getAttribute('data-tippy-trigger') || props.trigger || defaultProps.trigger;

      if (targetNode._tippy) {
        return;
      }

      if (event.type === 'touchstart' && typeof childProps.touch === 'boolean') {
        return;
      }

      if (event.type !== 'touchstart' && trigger.indexOf(BUBBLING_EVENTS_MAP[event.type]) < 0) {
        return;
      }

      var instance = tippy(targetNode, childProps);

      if (instance) {
        childTippyInstances = childTippyInstances.concat(instance);
      }
    }

    function on(node, eventType, handler, options) {
      if (options === void 0) {
        options = false;
      }

      node.addEventListener(eventType, handler, options);
      listeners.push({
        node: node,
        eventType: eventType,
        handler: handler,
        options: options
      });
    }

    function addEventListeners(instance) {
      var reference = instance.reference;
      on(reference, 'touchstart', onTrigger, TOUCH_OPTIONS);
      on(reference, 'mouseover', onTrigger);
      on(reference, 'focusin', onTrigger);
      on(reference, 'click', onTrigger);
    }

    function removeEventListeners() {
      listeners.forEach(function (_ref) {
        var node = _ref.node,
            eventType = _ref.eventType,
            handler = _ref.handler,
            options = _ref.options;
        node.removeEventListener(eventType, handler, options);
      });
      listeners = [];
    }

    function applyMutations(instance) {
      var originalDestroy = instance.destroy;
      var originalEnable = instance.enable;
      var originalDisable = instance.disable;

      instance.destroy = function (shouldDestroyChildInstances) {
        if (shouldDestroyChildInstances === void 0) {
          shouldDestroyChildInstances = true;
        }

        if (shouldDestroyChildInstances) {
          childTippyInstances.forEach(function (instance) {
            instance.destroy();
          });
        }

        childTippyInstances = [];
        removeEventListeners();
        originalDestroy();
      };

      instance.enable = function () {
        originalEnable();
        childTippyInstances.forEach(function (instance) {
          return instance.enable();
        });
        disabled = false;
      };

      instance.disable = function () {
        originalDisable();
        childTippyInstances.forEach(function (instance) {
          return instance.disable();
        });
        disabled = true;
      };

      addEventListeners(instance);
    }

    normalizedReturnValue.forEach(applyMutations);
    return returnValue;
  }

  var animateFill = {
    name: 'animateFill',
    defaultValue: false,
    fn: function fn(instance) {
      var _instance$props$rende;


      if (!((_instance$props$rende = instance.props.render) != null && _instance$props$rende.$$tippy)) {
        {
          errorWhen(instance.props.animateFill, 'The `animateFill` plugin requires the default render function.');
        }

        return {};
      }

      var _getChildren = getChildren(instance.popper),
          box = _getChildren.box,
          content = _getChildren.content;

      var backdrop = instance.props.animateFill ? createBackdropElement() : null;
      return {
        onCreate: function onCreate() {
          if (backdrop) {
            box.insertBefore(backdrop, box.firstElementChild);
            box.setAttribute('data-animatefill', '');
            box.style.overflow = 'hidden';
            instance.setProps({
              arrow: false,
              animation: 'shift-away'
            });
          }
        },
        onMount: function onMount() {
          if (backdrop) {
            var transitionDuration = box.style.transitionDuration;
            var duration = Number(transitionDuration.replace('ms', ''));



            content.style.transitionDelay = Math.round(duration / 10) + "ms";
            backdrop.style.transitionDuration = transitionDuration;
            setVisibilityState([backdrop], 'visible');
          }
        },
        onShow: function onShow() {
          if (backdrop) {
            backdrop.style.transitionDuration = '0ms';
          }
        },
        onHide: function onHide() {
          if (backdrop) {
            setVisibilityState([backdrop], 'hidden');
          }
        }
      };
    }
  };

  function createBackdropElement() {
    var backdrop = div();
    backdrop.className = BACKDROP_CLASS;
    setVisibilityState([backdrop], 'hidden');
    return backdrop;
  }

  var mouseCoords = {
    clientX: 0,
    clientY: 0
  };
  var activeInstances = [];

  function storeMouseCoords(_ref) {
    var clientX = _ref.clientX,
        clientY = _ref.clientY;
    mouseCoords = {
      clientX: clientX,
      clientY: clientY
    };
  }

  function addMouseCoordsListener(doc) {
    doc.addEventListener('mousemove', storeMouseCoords);
  }

  function removeMouseCoordsListener(doc) {
    doc.removeEventListener('mousemove', storeMouseCoords);
  }

  var followCursor = {
    name: 'followCursor',
    defaultValue: false,
    fn: function fn(instance) {
      var reference = instance.reference;
      var doc = getOwnerDocument(instance.props.triggerTarget || reference);
      var isInternalUpdate = false;
      var wasFocusEvent = false;
      var isUnmounted = true;
      var prevProps = instance.props;

      function getIsInitialBehavior() {
        return instance.props.followCursor === 'initial' && instance.state.isVisible;
      }

      function addListener() {
        doc.addEventListener('mousemove', onMouseMove);
      }

      function removeListener() {
        doc.removeEventListener('mousemove', onMouseMove);
      }

      function unsetGetReferenceClientRect() {
        isInternalUpdate = true;
        instance.setProps({
          getReferenceClientRect: null
        });
        isInternalUpdate = false;
      }

      function onMouseMove(event) {


        var isCursorOverReference = event.target ? reference.contains(event.target) : true;
        var followCursor = instance.props.followCursor;
        var clientX = event.clientX,
            clientY = event.clientY;
        var rect = reference.getBoundingClientRect();
        var relativeX = clientX - rect.left;
        var relativeY = clientY - rect.top;

        if (isCursorOverReference || !instance.props.interactive) {
          instance.setProps({

            getReferenceClientRect: function getReferenceClientRect() {
              var rect = reference.getBoundingClientRect();
              var x = clientX;
              var y = clientY;

              if (followCursor === 'initial') {
                x = rect.left + relativeX;
                y = rect.top + relativeY;
              }

              var top = followCursor === 'horizontal' ? rect.top : y;
              var right = followCursor === 'vertical' ? rect.right : x;
              var bottom = followCursor === 'horizontal' ? rect.bottom : y;
              var left = followCursor === 'vertical' ? rect.left : x;
              return {
                width: right - left,
                height: bottom - top,
                top: top,
                right: right,
                bottom: bottom,
                left: left
              };
            }
          });
        }
      }

      function create() {
        if (instance.props.followCursor) {
          activeInstances.push({
            instance: instance,
            doc: doc
          });
          addMouseCoordsListener(doc);
        }
      }

      function destroy() {
        activeInstances = activeInstances.filter(function (data) {
          return data.instance !== instance;
        });

        if (activeInstances.filter(function (data) {
          return data.doc === doc;
        }).length === 0) {
          removeMouseCoordsListener(doc);
        }
      }

      return {
        onCreate: create,
        onDestroy: destroy,
        onBeforeUpdate: function onBeforeUpdate() {
          prevProps = instance.props;
        },
        onAfterUpdate: function onAfterUpdate(_, _ref2) {
          var followCursor = _ref2.followCursor;

          if (isInternalUpdate) {
            return;
          }

          if (followCursor !== undefined && prevProps.followCursor !== followCursor) {
            destroy();

            if (followCursor) {
              create();

              if (instance.state.isMounted && !wasFocusEvent && !getIsInitialBehavior()) {
                addListener();
              }
            } else {
              removeListener();
              unsetGetReferenceClientRect();
            }
          }
        },
        onMount: function onMount() {
          if (instance.props.followCursor && !wasFocusEvent) {
            if (isUnmounted) {
              onMouseMove(mouseCoords);
              isUnmounted = false;
            }

            if (!getIsInitialBehavior()) {
              addListener();
            }
          }
        },
        onTrigger: function onTrigger(_, event) {
          if (isMouseEvent(event)) {
            mouseCoords = {
              clientX: event.clientX,
              clientY: event.clientY
            };
          }

          wasFocusEvent = event.type === 'focus';
        },
        onHidden: function onHidden() {
          if (instance.props.followCursor) {
            unsetGetReferenceClientRect();
            removeListener();
            isUnmounted = true;
          }
        }
      };
    }
  };

  function getProps(props, modifier) {
    var _props$popperOptions;

    return {
      popperOptions: Object.assign({}, props.popperOptions, {
        modifiers: [].concat((((_props$popperOptions = props.popperOptions) == null ? void 0 : _props$popperOptions.modifiers) || []).filter(function (_ref) {
          var name = _ref.name;
          return name !== modifier.name;
        }), [modifier])
      })
    };
  }

  var inlinePositioning = {
    name: 'inlinePositioning',
    defaultValue: false,
    fn: function fn(instance) {
      var reference = instance.reference;

      function isEnabled() {
        return !!instance.props.inlinePositioning;
      }

      var placement;
      var cursorRectIndex = -1;
      var isInternalUpdate = false;
      var triedPlacements = [];
      var modifier = {
        name: 'tippyInlinePositioning',
        enabled: true,
        phase: 'afterWrite',
        fn: function fn(_ref2) {
          var state = _ref2.state;

          if (isEnabled()) {
            if (triedPlacements.indexOf(state.placement) !== -1) {
              triedPlacements = [];
            }

            if (placement !== state.placement && triedPlacements.indexOf(state.placement) === -1) {
              triedPlacements.push(state.placement);
              instance.setProps({

                getReferenceClientRect: function getReferenceClientRect() {
                  return _getReferenceClientRect(state.placement);
                }
              });
            }

            placement = state.placement;
          }
        }
      };

      function _getReferenceClientRect(placement) {
        return getInlineBoundingClientRect(getBasePlacement(placement), reference.getBoundingClientRect(), arrayFrom(reference.getClientRects()), cursorRectIndex);
      }

      function setInternalProps(partialProps) {
        isInternalUpdate = true;
        instance.setProps(partialProps);
        isInternalUpdate = false;
      }

      function addModifier() {
        if (!isInternalUpdate) {
          setInternalProps(getProps(instance.props, modifier));
        }
      }

      return {
        onCreate: addModifier,
        onAfterUpdate: addModifier,
        onTrigger: function onTrigger(_, event) {
          if (isMouseEvent(event)) {
            var rects = arrayFrom(instance.reference.getClientRects());
            var cursorRect = rects.find(function (rect) {
              return rect.left - 2 <= event.clientX && rect.right + 2 >= event.clientX && rect.top - 2 <= event.clientY && rect.bottom + 2 >= event.clientY;
            });
            var index = rects.indexOf(cursorRect);
            cursorRectIndex = index > -1 ? index : cursorRectIndex;
          }
        },
        onHidden: function onHidden() {
          cursorRectIndex = -1;
        }
      };
    }
  };
  function getInlineBoundingClientRect(currentBasePlacement, boundingRect, clientRects, cursorRectIndex) {

    if (clientRects.length < 2 || currentBasePlacement === null) {
      return boundingRect;
    }


    if (clientRects.length === 2 && cursorRectIndex >= 0 && clientRects[0].left > clientRects[1].right) {
      return clientRects[cursorRectIndex] || boundingRect;
    }

    switch (currentBasePlacement) {
      case 'top':
      case 'bottom':
        {
          var firstRect = clientRects[0];
          var lastRect = clientRects[clientRects.length - 1];
          var isTop = currentBasePlacement === 'top';
          var top = firstRect.top;
          var bottom = lastRect.bottom;
          var left = isTop ? firstRect.left : lastRect.left;
          var right = isTop ? firstRect.right : lastRect.right;
          var width = right - left;
          var height = bottom - top;
          return {
            top: top,
            bottom: bottom,
            left: left,
            right: right,
            width: width,
            height: height
          };
        }

      case 'left':
      case 'right':
        {
          var minLeft = Math.min.apply(Math, clientRects.map(function (rects) {
            return rects.left;
          }));
          var maxRight = Math.max.apply(Math, clientRects.map(function (rects) {
            return rects.right;
          }));
          var measureRects = clientRects.filter(function (rect) {
            return currentBasePlacement === 'left' ? rect.left === minLeft : rect.right === maxRight;
          });
          var _top = measureRects[0].top;
          var _bottom = measureRects[measureRects.length - 1].bottom;
          var _left = minLeft;
          var _right = maxRight;

          var _width = _right - _left;

          var _height = _bottom - _top;

          return {
            top: _top,
            bottom: _bottom,
            left: _left,
            right: _right,
            width: _width,
            height: _height
          };
        }

      default:
        {
          return boundingRect;
        }
    }
  }

  var sticky = {
    name: 'sticky',
    defaultValue: false,
    fn: function fn(instance) {
      var reference = instance.reference,
          popper = instance.popper;

      function getReference() {
        return instance.popperInstance ? instance.popperInstance.state.elements.reference : reference;
      }

      function shouldCheck(value) {
        return instance.props.sticky === true || instance.props.sticky === value;
      }

      var prevRefRect = null;
      var prevPopRect = null;

      function updatePosition() {
        var currentRefRect = shouldCheck('reference') ? getReference().getBoundingClientRect() : null;
        var currentPopRect = shouldCheck('popper') ? popper.getBoundingClientRect() : null;

        if (currentRefRect && areRectsDifferent(prevRefRect, currentRefRect) || currentPopRect && areRectsDifferent(prevPopRect, currentPopRect)) {
          if (instance.popperInstance) {
            instance.popperInstance.update();
          }
        }

        prevRefRect = currentRefRect;
        prevPopRect = currentPopRect;

        if (instance.state.isMounted) {
          requestAnimationFrame(updatePosition);
        }
      }

      return {
        onMount: function onMount() {
          if (instance.props.sticky) {
            updatePosition();
          }
        }
      };
    }
  };

  function areRectsDifferent(rectA, rectB) {
    if (rectA && rectB) {
      return rectA.top !== rectB.top || rectA.right !== rectB.right || rectA.bottom !== rectB.bottom || rectA.left !== rectB.left;
    }

    return true;
  }

  if (isBrowser) {
    injectCSS(css);
  }

  tippy.setDefaultProps({
    plugins: [animateFill, followCursor, inlinePositioning, sticky],
    render: render
  });
  tippy.createSingleton = createSingleton;
  tippy.delegate = delegate;
  tippy.hideAll = hideAll;
  tippy.roundArrow = ROUND_ARROW;

  return tippy;

})));

;



(() => {

  function src_default(Alpine) {
    let persist = () => {
      let alias;
      let storage;
      try {
        storage = localStorage;
      } catch (e) {
        console.error(e);
        console.warn("Alpine: $persist is using temporary storage since localStorage is unavailable.");
        let dummy =  new Map();
        storage = {
          getItem: dummy.get.bind(dummy),
          setItem: dummy.set.bind(dummy)
        };
      }
      return Alpine.interceptor((initialValue, getter, setter, path, key) => {
        let lookup = alias || `_x_${path}`;
        let initial = storageHas(lookup, storage) ? storageGet(lookup, storage) : initialValue;
        setter(initial);
        Alpine.effect(() => {
          let value = getter();
          storageSet(lookup, value, storage);
          setter(value);
        });
        return initial;
      }, (func) => {
        func.as = (key) => {
          alias = key;
          return func;
        }, func.using = (target) => {
          storage = target;
          return func;
        };
      });
    };
    Object.defineProperty(Alpine, "$persist", { get: () => persist() });
    Alpine.magic("persist", persist);
    Alpine.persist = (key, { get, set }, storage = localStorage) => {
      let initial = storageHas(key, storage) ? storageGet(key, storage) : get();
      set(initial);
      Alpine.effect(() => {
        let value = get();
        storageSet(key, value, storage);
        set(value);
      });
    };
  }
  function storageHas(key, storage) {
    return storage.getItem(key) !== null;
  }
  function storageGet(key, storage) {
    let value = storage.getItem(key, storage);
    if (value === void 0)
      return;
    return JSON.parse(value);
  }
  function storageSet(key, value, storage) {
    storage.setItem(key, JSON.stringify(value));
  }


  document.addEventListener("alpine:init", () => {
    window.Alpine.plugin(src_default);
  });
})();
;



(() => {

  function src_default(Alpine) {
    Alpine.directive("collapse", collapse);
    collapse.inline = (el, { modifiers }) => {
      if (!modifiers.includes("min"))
        return;
      el._x_doShow = () => {
      };
      el._x_doHide = () => {
      };
    };
    function collapse(el, { modifiers }) {
      let duration = modifierValue(modifiers, "duration", 250) / 1e3;
      let floor = modifierValue(modifiers, "min", 0);
      let fullyHide = !modifiers.includes("min");
      if (!el._x_isShown)
        el.style.height = `${floor}px`;
      if (!el._x_isShown && fullyHide)
        el.hidden = true;
      if (!el._x_isShown)
        el.style.overflow = "hidden";
      let setFunction = (el2, styles) => {
        let revertFunction = Alpine.setStyles(el2, styles);
        return styles.height ? () => {
        } : revertFunction;
      };
      let transitionStyles = {
        transitionProperty: "height",
        transitionDuration: `${duration}s`,
        transitionTimingFunction: "cubic-bezier(0.4, 0.0, 0.2, 1)"
      };
      el._x_transition = {
        in(before = () => {
        }, after = () => {
        }) {
          if (fullyHide)
            el.hidden = false;
          if (fullyHide)
            el.style.display = null;
          let current = el.getBoundingClientRect().height;
          el.style.height = "auto";
          let full = el.getBoundingClientRect().height;
          if (current === full) {
            current = floor;
          }
          Alpine.transition(el, Alpine.setStyles, {
            during: transitionStyles,
            start: { height: current + "px" },
            end: { height: full + "px" }
          }, () => el._x_isShown = true, () => {
            if (Math.abs(el.getBoundingClientRect().height - full) < 1) {
              el.style.overflow = null;
            }
          });
        },
        out(before = () => {
        }, after = () => {
        }) {
          let full = el.getBoundingClientRect().height;
          Alpine.transition(el, setFunction, {
            during: transitionStyles,
            start: { height: full + "px" },
            end: { height: floor + "px" }
          }, () => el.style.overflow = "hidden", () => {
            el._x_isShown = false;
            if (el.style.height == `${floor}px` && fullyHide) {
              el.style.display = "none";
              el.hidden = true;
            }
          });
        }
      };
    }
  }
  function modifierValue(modifiers, key, fallback) {
    if (modifiers.indexOf(key) === -1)
      return fallback;
    const rawValue = modifiers[modifiers.indexOf(key) + 1];
    if (!rawValue)
      return fallback;
    if (key === "duration") {
      let match = rawValue.match(/([0-9]+)ms/);
      if (match)
        return match[1];
    }
    if (key === "min") {
      let match = rawValue.match(/([0-9]+)px/);
      if (match)
        return match[1];
    }
    return rawValue;
  }


  document.addEventListener("alpine:init", () => {
    window.Alpine.plugin(src_default);
  });
})();
;



(() => {

  var flushPending = false;
  var flushing = false;
  var queue = [];
  var lastFlushedIndex = -1;
  function scheduler(callback) {
    queueJob(callback);
  }
  function queueJob(job) {
    if (!queue.includes(job))
      queue.push(job);
    queueFlush();
  }
  function dequeueJob(job) {
    let index = queue.indexOf(job);
    if (index !== -1 && index > lastFlushedIndex)
      queue.splice(index, 1);
  }
  function queueFlush() {
    if (!flushing && !flushPending) {
      flushPending = true;
      queueMicrotask(flushJobs);
    }
  }
  function flushJobs() {
    flushPending = false;
    flushing = true;
    for (let i = 0; i < queue.length; i++) {
      queue[i]();
      lastFlushedIndex = i;
    }
    queue.length = 0;
    lastFlushedIndex = -1;
    flushing = false;
  }


  var reactive;
  var effect;
  var release;
  var raw;
  var shouldSchedule = true;
  function disableEffectScheduling(callback) {
    shouldSchedule = false;
    callback();
    shouldSchedule = true;
  }
  function setReactivityEngine(engine) {
    reactive = engine.reactive;
    release = engine.release;
    effect = (callback) => engine.effect(callback, { scheduler: (task) => {
      if (shouldSchedule) {
        scheduler(task);
      } else {
        task();
      }
    } });
    raw = engine.raw;
  }
  function overrideEffect(override) {
    effect = override;
  }
  function elementBoundEffect(el) {
    let cleanup2 = () => {
    };
    let wrappedEffect = (callback) => {
      let effectReference = effect(callback);
      if (!el._x_effects) {
        el._x_effects =  new Set();
        el._x_runEffects = () => {
          el._x_effects.forEach((i) => i());
        };
      }
      el._x_effects.add(effectReference);
      cleanup2 = () => {
        if (effectReference === void 0)
          return;
        el._x_effects.delete(effectReference);
        release(effectReference);
      };
      return effectReference;
    };
    return [wrappedEffect, () => {
      cleanup2();
    }];
  }
  function watch(getter, callback) {
    let firstTime = true;
    let oldValue;
    let effectReference = effect(() => {
      let value = getter();
      JSON.stringify(value);
      if (!firstTime) {
        queueMicrotask(() => {
          callback(value, oldValue);
          oldValue = value;
        });
      } else {
        oldValue = value;
      }
      firstTime = false;
    });
    return () => release(effectReference);
  }


  var onAttributeAddeds = [];
  var onElRemoveds = [];
  var onElAddeds = [];
  function onElAdded(callback) {
    onElAddeds.push(callback);
  }
  function onElRemoved(el, callback) {
    if (typeof callback === "function") {
      if (!el._x_cleanups)
        el._x_cleanups = [];
      el._x_cleanups.push(callback);
    } else {
      callback = el;
      onElRemoveds.push(callback);
    }
  }
  function onAttributesAdded(callback) {
    onAttributeAddeds.push(callback);
  }
  function onAttributeRemoved(el, name, callback) {
    if (!el._x_attributeCleanups)
      el._x_attributeCleanups = {};
    if (!el._x_attributeCleanups[name])
      el._x_attributeCleanups[name] = [];
    el._x_attributeCleanups[name].push(callback);
  }
  function cleanupAttributes(el, names) {
    if (!el._x_attributeCleanups)
      return;
    Object.entries(el._x_attributeCleanups).forEach(([name, value]) => {
      if (names === void 0 || names.includes(name)) {
        value.forEach((i) => i());
        delete el._x_attributeCleanups[name];
      }
    });
  }
  function cleanupElement(el) {
    el._x_effects?.forEach(dequeueJob);
    while (el._x_cleanups?.length)
      el._x_cleanups.pop()();
  }
  var observer = new MutationObserver(onMutate);
  var currentlyObserving = false;
  function startObservingMutations() {
    observer.observe(document, { subtree: true, childList: true, attributes: true, attributeOldValue: true });
    currentlyObserving = true;
  }
  function stopObservingMutations() {
    flushObserver();
    observer.disconnect();
    currentlyObserving = false;
  }
  var queuedMutations = [];
  function flushObserver() {
    let records = observer.takeRecords();
    queuedMutations.push(() => records.length > 0 && onMutate(records));
    let queueLengthWhenTriggered = queuedMutations.length;
    queueMicrotask(() => {
      if (queuedMutations.length === queueLengthWhenTriggered) {
        while (queuedMutations.length > 0)
          queuedMutations.shift()();
      }
    });
  }
  function mutateDom(callback) {
    if (!currentlyObserving)
      return callback();
    stopObservingMutations();
    let result = callback();
    startObservingMutations();
    return result;
  }
  var isCollecting = false;
  var deferredMutations = [];
  function deferMutations() {
    isCollecting = true;
  }
  function flushAndStopDeferringMutations() {
    isCollecting = false;
    onMutate(deferredMutations);
    deferredMutations = [];
  }
  function onMutate(mutations) {
    if (isCollecting) {
      deferredMutations = deferredMutations.concat(mutations);
      return;
    }
    let addedNodes = [];
    let removedNodes =  new Set();
    let addedAttributes =  new Map();
    let removedAttributes =  new Map();
    for (let i = 0; i < mutations.length; i++) {
      if (mutations[i].target._x_ignoreMutationObserver)
        continue;
      if (mutations[i].type === "childList") {
        mutations[i].removedNodes.forEach((node) => {
          if (node.nodeType !== 1)
            return;
          if (!node._x_marker)
            return;
          removedNodes.add(node);
        });
        mutations[i].addedNodes.forEach((node) => {
          if (node.nodeType !== 1)
            return;
          if (removedNodes.has(node)) {
            removedNodes.delete(node);
            return;
          }
          if (node._x_marker)
            return;
          addedNodes.push(node);
        });
      }
      if (mutations[i].type === "attributes") {
        let el = mutations[i].target;
        let name = mutations[i].attributeName;
        let oldValue = mutations[i].oldValue;
        let add2 = () => {
          if (!addedAttributes.has(el))
            addedAttributes.set(el, []);
          addedAttributes.get(el).push({ name, value: el.getAttribute(name) });
        };
        let remove = () => {
          if (!removedAttributes.has(el))
            removedAttributes.set(el, []);
          removedAttributes.get(el).push(name);
        };
        if (el.hasAttribute(name) && oldValue === null) {
          add2();
        } else if (el.hasAttribute(name)) {
          remove();
          add2();
        } else {
          remove();
        }
      }
    }
    removedAttributes.forEach((attrs, el) => {
      cleanupAttributes(el, attrs);
    });
    addedAttributes.forEach((attrs, el) => {
      onAttributeAddeds.forEach((i) => i(el, attrs));
    });
    for (let node of removedNodes) {
      if (addedNodes.some((i) => i.contains(node)))
        continue;
      onElRemoveds.forEach((i) => i(node));
    }
    for (let node of addedNodes) {
      if (!node.isConnected)
        continue;
      onElAddeds.forEach((i) => i(node));
    }
    addedNodes = null;
    removedNodes = null;
    addedAttributes = null;
    removedAttributes = null;
  }


  function scope(node) {
    return mergeProxies(closestDataStack(node));
  }
  function addScopeToNode(node, data2, referenceNode) {
    node._x_dataStack = [data2, ...closestDataStack(referenceNode || node)];
    return () => {
      node._x_dataStack = node._x_dataStack.filter((i) => i !== data2);
    };
  }
  function closestDataStack(node) {
    if (node._x_dataStack)
      return node._x_dataStack;
    if (typeof ShadowRoot === "function" && node instanceof ShadowRoot) {
      return closestDataStack(node.host);
    }
    if (!node.parentNode) {
      return [];
    }
    return closestDataStack(node.parentNode);
  }
  function mergeProxies(objects) {
    return new Proxy({ objects }, mergeProxyTrap);
  }
  var mergeProxyTrap = {
    ownKeys({ objects }) {
      return Array.from(
        new Set(objects.flatMap((i) => Object.keys(i)))
      );
    },
    has({ objects }, name) {
      if (name == Symbol.unscopables)
        return false;
      return objects.some(
        (obj) => Object.prototype.hasOwnProperty.call(obj, name) || Reflect.has(obj, name)
      );
    },
    get({ objects }, name, thisProxy) {
      if (name == "toJSON")
        return collapseProxies;
      return Reflect.get(
        objects.find(
          (obj) => Reflect.has(obj, name)
        ) || {},
        name,
        thisProxy
      );
    },
    set({ objects }, name, value, thisProxy) {
      const target = objects.find(
        (obj) => Object.prototype.hasOwnProperty.call(obj, name)
      ) || objects[objects.length - 1];
      const descriptor = Object.getOwnPropertyDescriptor(target, name);
      if (descriptor?.set && descriptor?.get)
        return descriptor.set.call(thisProxy, value) || true;
      return Reflect.set(target, name, value);
    }
  };
  function collapseProxies() {
    let keys = Reflect.ownKeys(this);
    return keys.reduce((acc, key) => {
      acc[key] = Reflect.get(this, key);
      return acc;
    }, {});
  }


  function initInterceptors(data2) {
    let isObject2 = (val) => typeof val === "object" && !Array.isArray(val) && val !== null;
    let recurse = (obj, basePath = "") => {
      Object.entries(Object.getOwnPropertyDescriptors(obj)).forEach(([key, { value, enumerable }]) => {
        if (enumerable === false || value === void 0)
          return;
        if (typeof value === "object" && value !== null && value.__v_skip)
          return;
        let path = basePath === "" ? key : `${basePath}.${key}`;
        if (typeof value === "object" && value !== null && value._x_interceptor) {
          obj[key] = value.initialize(data2, path, key);
        } else {
          if (isObject2(value) && value !== obj && !(value instanceof Element)) {
            recurse(value, path);
          }
        }
      });
    };
    return recurse(data2);
  }
  function interceptor(callback, mutateObj = () => {
  }) {
    let obj = {
      initialValue: void 0,
      _x_interceptor: true,
      initialize(data2, path, key) {
        return callback(this.initialValue, () => get(data2, path), (value) => set(data2, path, value), path, key);
      }
    };
    mutateObj(obj);
    return (initialValue) => {
      if (typeof initialValue === "object" && initialValue !== null && initialValue._x_interceptor) {
        let initialize = obj.initialize.bind(obj);
        obj.initialize = (data2, path, key) => {
          let innerValue = initialValue.initialize(data2, path, key);
          obj.initialValue = innerValue;
          return initialize(data2, path, key);
        };
      } else {
        obj.initialValue = initialValue;
      }
      return obj;
    };
  }
  function get(obj, path) {
    return path.split(".").reduce((carry, segment) => carry[segment], obj);
  }
  function set(obj, path, value) {
    if (typeof path === "string")
      path = path.split(".");
    if (path.length === 1)
      obj[path[0]] = value;
    else if (path.length === 0)
      throw error;
    else {
      if (obj[path[0]])
        return set(obj[path[0]], path.slice(1), value);
      else {
        obj[path[0]] = {};
        return set(obj[path[0]], path.slice(1), value);
      }
    }
  }


  var magics = {};
  function magic(name, callback) {
    magics[name] = callback;
  }
  function injectMagics(obj, el) {
    let memoizedUtilities = getUtilities(el);
    Object.entries(magics).forEach(([name, callback]) => {
      Object.defineProperty(obj, `$${name}`, {
        get() {
          return callback(el, memoizedUtilities);
        },
        enumerable: false
      });
    });
    return obj;
  }
  function getUtilities(el) {
    let [utilities, cleanup2] = getElementBoundUtilities(el);
    let utils = { interceptor, ...utilities };
    onElRemoved(el, cleanup2);
    return utils;
  }


  function tryCatch(el, expression, callback, ...args) {
    try {
      return callback(...args);
    } catch (e) {
      handleError(e, el, expression);
    }
  }
  function handleError(error2, el, expression = void 0) {
    error2 = Object.assign(
      error2 ?? { message: "No error message given." },
      { el, expression }
    );
    console.warn(`Alpine Expression Error: ${error2.message}

${expression ? 'Expression: "' + expression + '"\n\n' : ""}`, el);
    setTimeout(() => {
      throw error2;
    }, 0);
  }


  var shouldAutoEvaluateFunctions = true;
  function dontAutoEvaluateFunctions(callback) {
    let cache = shouldAutoEvaluateFunctions;
    shouldAutoEvaluateFunctions = false;
    let result = callback();
    shouldAutoEvaluateFunctions = cache;
    return result;
  }
  function evaluate(el, expression, extras = {}) {
    let result;
    evaluateLater(el, expression)((value) => result = value, extras);
    return result;
  }
  function evaluateLater(...args) {
    return theEvaluatorFunction(...args);
  }
  var theEvaluatorFunction = normalEvaluator;
  function setEvaluator(newEvaluator) {
    theEvaluatorFunction = newEvaluator;
  }
  function normalEvaluator(el, expression) {
    let overriddenMagics = {};
    injectMagics(overriddenMagics, el);
    let dataStack = [overriddenMagics, ...closestDataStack(el)];
    let evaluator = typeof expression === "function" ? generateEvaluatorFromFunction(dataStack, expression) : generateEvaluatorFromString(dataStack, expression, el);
    return tryCatch.bind(null, el, expression, evaluator);
  }
  function generateEvaluatorFromFunction(dataStack, func) {
    return (receiver = () => {
    }, { scope: scope2 = {}, params = [] } = {}) => {
      let result = func.apply(mergeProxies([scope2, ...dataStack]), params);
      runIfTypeOfFunction(receiver, result);
    };
  }
  var evaluatorMemo = {};
  function generateFunctionFromString(expression, el) {
    if (evaluatorMemo[expression]) {
      return evaluatorMemo[expression];
    }
    let AsyncFunction = Object.getPrototypeOf(async function() {
    }).constructor;
    let rightSideSafeExpression = /^[\n\s]*if.*\(.*\)/.test(expression.trim()) || /^(let|const)\s/.test(expression.trim()) ? `(async()=>{ ${expression} })()` : expression;
    const safeAsyncFunction = () => {
      try {
        let func2 = new AsyncFunction(
          ["__self", "scope"],
          `with (scope) { __self.result = ${rightSideSafeExpression} }; __self.finished = true; return __self.result;`
        );
        Object.defineProperty(func2, "name", {
          value: `[Alpine] ${expression}`
        });
        return func2;
      } catch (error2) {
        handleError(error2, el, expression);
        return Promise.resolve();
      }
    };
    let func = safeAsyncFunction();
    evaluatorMemo[expression] = func;
    return func;
  }
  function generateEvaluatorFromString(dataStack, expression, el) {
    let func = generateFunctionFromString(expression, el);
    return (receiver = () => {
    }, { scope: scope2 = {}, params = [] } = {}) => {
      func.result = void 0;
      func.finished = false;
      let completeScope = mergeProxies([scope2, ...dataStack]);
      if (typeof func === "function") {
        let promise = func(func, completeScope).catch((error2) => handleError(error2, el, expression));
        if (func.finished) {
          runIfTypeOfFunction(receiver, func.result, completeScope, params, el);
          func.result = void 0;
        } else {
          promise.then((result) => {
            runIfTypeOfFunction(receiver, result, completeScope, params, el);
          }).catch((error2) => handleError(error2, el, expression)).finally(() => func.result = void 0);
        }
      }
    };
  }
  function runIfTypeOfFunction(receiver, value, scope2, params, el) {
    if (shouldAutoEvaluateFunctions && typeof value === "function") {
      let result = value.apply(scope2, params);
      if (result instanceof Promise) {
        result.then((i) => runIfTypeOfFunction(receiver, i, scope2, params)).catch((error2) => handleError(error2, el, value));
      } else {
        receiver(result);
      }
    } else if (typeof value === "object" && value instanceof Promise) {
      value.then((i) => receiver(i));
    } else {
      receiver(value);
    }
  }


  var prefixAsString = "x-";
  function prefix(subject = "") {
    return prefixAsString + subject;
  }
  function setPrefix(newPrefix) {
    prefixAsString = newPrefix;
  }
  var directiveHandlers = {};
  function directive(name, callback) {
    directiveHandlers[name] = callback;
    return {
      before(directive2) {
        if (!directiveHandlers[directive2]) {
          console.warn(String.raw`Cannot find directive \`${directive2}\`. \`${name}\` will use the default order of execution`);
          return;
        }
        const pos = directiveOrder.indexOf(directive2);
        directiveOrder.splice(pos >= 0 ? pos : directiveOrder.indexOf("DEFAULT"), 0, name);
      }
    };
  }
  function directiveExists(name) {
    return Object.keys(directiveHandlers).includes(name);
  }
  function directives(el, attributes, originalAttributeOverride) {
    attributes = Array.from(attributes);
    if (el._x_virtualDirectives) {
      let vAttributes = Object.entries(el._x_virtualDirectives).map(([name, value]) => ({ name, value }));
      let staticAttributes = attributesOnly(vAttributes);
      vAttributes = vAttributes.map((attribute) => {
        if (staticAttributes.find((attr) => attr.name === attribute.name)) {
          return {
            name: `x-bind:${attribute.name}`,
            value: `"${attribute.value}"`
          };
        }
        return attribute;
      });
      attributes = attributes.concat(vAttributes);
    }
    let transformedAttributeMap = {};
    let directives2 = attributes.map(toTransformedAttributes((newName, oldName) => transformedAttributeMap[newName] = oldName)).filter(outNonAlpineAttributes).map(toParsedDirectives(transformedAttributeMap, originalAttributeOverride)).sort(byPriority);
    return directives2.map((directive2) => {
      return getDirectiveHandler(el, directive2);
    });
  }
  function attributesOnly(attributes) {
    return Array.from(attributes).map(toTransformedAttributes()).filter((attr) => !outNonAlpineAttributes(attr));
  }
  var isDeferringHandlers = false;
  var directiveHandlerStacks =  new Map();
  var currentHandlerStackKey = Symbol();
  function deferHandlingDirectives(callback) {
    isDeferringHandlers = true;
    let key = Symbol();
    currentHandlerStackKey = key;
    directiveHandlerStacks.set(key, []);
    let flushHandlers = () => {
      while (directiveHandlerStacks.get(key).length)
        directiveHandlerStacks.get(key).shift()();
      directiveHandlerStacks.delete(key);
    };
    let stopDeferring = () => {
      isDeferringHandlers = false;
      flushHandlers();
    };
    callback(flushHandlers);
    stopDeferring();
  }
  function getElementBoundUtilities(el) {
    let cleanups = [];
    let cleanup2 = (callback) => cleanups.push(callback);
    let [effect3, cleanupEffect] = elementBoundEffect(el);
    cleanups.push(cleanupEffect);
    let utilities = {
      Alpine: alpine_default,
      effect: effect3,
      cleanup: cleanup2,
      evaluateLater: evaluateLater.bind(evaluateLater, el),
      evaluate: evaluate.bind(evaluate, el)
    };
    let doCleanup = () => cleanups.forEach((i) => i());
    return [utilities, doCleanup];
  }
  function getDirectiveHandler(el, directive2) {
    let noop = () => {
    };
    let handler4 = directiveHandlers[directive2.type] || noop;
    let [utilities, cleanup2] = getElementBoundUtilities(el);
    onAttributeRemoved(el, directive2.original, cleanup2);
    let fullHandler = () => {
      if (el._x_ignore || el._x_ignoreSelf)
        return;
      handler4.inline && handler4.inline(el, directive2, utilities);
      handler4 = handler4.bind(handler4, el, directive2, utilities);
      isDeferringHandlers ? directiveHandlerStacks.get(currentHandlerStackKey).push(handler4) : handler4();
    };
    fullHandler.runCleanups = cleanup2;
    return fullHandler;
  }
  var startingWith = (subject, replacement) => ({ name, value }) => {
    if (name.startsWith(subject))
      name = name.replace(subject, replacement);
    return { name, value };
  };
  var into = (i) => i;
  function toTransformedAttributes(callback = () => {
  }) {
    return ({ name, value }) => {
      let { name: newName, value: newValue } = attributeTransformers.reduce((carry, transform) => {
        return transform(carry);
      }, { name, value });
      if (newName !== name)
        callback(newName, name);
      return { name: newName, value: newValue };
    };
  }
  var attributeTransformers = [];
  function mapAttributes(callback) {
    attributeTransformers.push(callback);
  }
  function outNonAlpineAttributes({ name }) {
    return alpineAttributeRegex().test(name);
  }
  var alpineAttributeRegex = () => new RegExp(`^${prefixAsString}([^:^.]+)\\b`);
  function toParsedDirectives(transformedAttributeMap, originalAttributeOverride) {
    return ({ name, value }) => {
      let typeMatch = name.match(alpineAttributeRegex());
      let valueMatch = name.match(/:([a-zA-Z0-9\-_:]+)/);
      let modifiers = name.match(/\.[^.\]]+(?=[^\]]*$)/g) || [];
      let original = originalAttributeOverride || transformedAttributeMap[name] || name;
      return {
        type: typeMatch ? typeMatch[1] : null,
        value: valueMatch ? valueMatch[1] : null,
        modifiers: modifiers.map((i) => i.replace(".", "")),
        expression: value,
        original
      };
    };
  }
  var DEFAULT = "DEFAULT";
  var directiveOrder = [
    "ignore",
    "ref",
    "data",
    "id",
    "anchor",
    "bind",
    "init",
    "for",
    "model",
    "modelable",
    "transition",
    "show",
    "if",
    DEFAULT,
    "teleport"
  ];
  function byPriority(a, b) {
    let typeA = directiveOrder.indexOf(a.type) === -1 ? DEFAULT : a.type;
    let typeB = directiveOrder.indexOf(b.type) === -1 ? DEFAULT : b.type;
    return directiveOrder.indexOf(typeA) - directiveOrder.indexOf(typeB);
  }


  function dispatch(el, name, detail = {}) {
    el.dispatchEvent(
      new CustomEvent(name, {
        detail,
        bubbles: true,

        composed: true,
        cancelable: true
      })
    );
  }


  function walk(el, callback) {
    if (typeof ShadowRoot === "function" && el instanceof ShadowRoot) {
      Array.from(el.children).forEach((el2) => walk(el2, callback));
      return;
    }
    let skip = false;
    callback(el, () => skip = true);
    if (skip)
      return;
    let node = el.firstElementChild;
    while (node) {
      walk(node, callback, false);
      node = node.nextElementSibling;
    }
  }


  function warn(message, ...args) {
    console.warn(`Alpine Warning: ${message}`, ...args);
  }


  var started = false;
  function start() {
    if (started)
      warn("Alpine has already been initialized on this page. Calling Alpine.start() more than once can cause problems.");
    started = true;
    if (!document.body)
      warn("Unable to initialize. Trying to load Alpine before `<body>` is available. Did you forget to add `defer` in Alpine's `<script>` tag?");
    dispatch(document, "alpine:init");
    dispatch(document, "alpine:initializing");
    startObservingMutations();
    onElAdded((el) => initTree(el, walk));
    onElRemoved((el) => destroyTree(el));
    onAttributesAdded((el, attrs) => {
      directives(el, attrs).forEach((handle) => handle());
    });
    let outNestedComponents = (el) => !closestRoot(el.parentElement, true);
    Array.from(document.querySelectorAll(allSelectors().join(","))).filter(outNestedComponents).forEach((el) => {
      initTree(el);
    });
    dispatch(document, "alpine:initialized");
    setTimeout(() => {
      warnAboutMissingPlugins();
    });
  }
  var rootSelectorCallbacks = [];
  var initSelectorCallbacks = [];
  function rootSelectors() {
    return rootSelectorCallbacks.map((fn) => fn());
  }
  function allSelectors() {
    return rootSelectorCallbacks.concat(initSelectorCallbacks).map((fn) => fn());
  }
  function addRootSelector(selectorCallback) {
    rootSelectorCallbacks.push(selectorCallback);
  }
  function addInitSelector(selectorCallback) {
    initSelectorCallbacks.push(selectorCallback);
  }
  function closestRoot(el, includeInitSelectors = false) {
    return findClosest(el, (element) => {
      const selectors = includeInitSelectors ? allSelectors() : rootSelectors();
      if (selectors.some((selector) => element.matches(selector)))
        return true;
    });
  }
  function findClosest(el, callback) {
    if (!el)
      return;
    if (callback(el))
      return el;
    if (el._x_teleportBack)
      el = el._x_teleportBack;
    if (!el.parentElement)
      return;
    return findClosest(el.parentElement, callback);
  }
  function isRoot(el) {
    return rootSelectors().some((selector) => el.matches(selector));
  }
  var initInterceptors2 = [];
  function interceptInit(callback) {
    initInterceptors2.push(callback);
  }
  var markerDispenser = 1;
  function initTree(el, walker = walk, intercept = () => {
  }) {
    if (findClosest(el, (i) => i._x_ignore))
      return;
    deferHandlingDirectives(() => {
      walker(el, (el2, skip) => {
        if (el2._x_marker)
          return;
        intercept(el2, skip);
        initInterceptors2.forEach((i) => i(el2, skip));
        directives(el2, el2.attributes).forEach((handle) => handle());
        if (!el2._x_ignore)
          el2._x_marker = markerDispenser++;
        el2._x_ignore && skip();
      });
    });
  }
  function destroyTree(root, walker = walk) {
    walker(root, (el) => {
      cleanupElement(el);
      cleanupAttributes(el);
      delete el._x_marker;
    });
  }
  function warnAboutMissingPlugins() {
    let pluginDirectives = [
      ["ui", "dialog", ["[x-dialog], [x-popover]"]],
      ["anchor", "anchor", ["[x-anchor]"]],
      ["sort", "sort", ["[x-sort]"]]
    ];
    pluginDirectives.forEach(([plugin2, directive2, selectors]) => {
      if (directiveExists(directive2))
        return;
      selectors.some((selector) => {
        if (document.querySelector(selector)) {
          warn(`found "${selector}", but missing ${plugin2} plugin`);
          return true;
        }
      });
    });
  }


  var tickStack = [];
  var isHolding = false;
  function nextTick(callback = () => {
  }) {
    queueMicrotask(() => {
      isHolding || setTimeout(() => {
        releaseNextTicks();
      });
    });
    return new Promise((res) => {
      tickStack.push(() => {
        callback();
        res();
      });
    });
  }
  function releaseNextTicks() {
    isHolding = false;
    while (tickStack.length)
      tickStack.shift()();
  }
  function holdNextTicks() {
    isHolding = true;
  }


  function setClasses(el, value) {
    if (Array.isArray(value)) {
      return setClassesFromString(el, value.join(" "));
    } else if (typeof value === "object" && value !== null) {
      return setClassesFromObject(el, value);
    } else if (typeof value === "function") {
      return setClasses(el, value());
    }
    return setClassesFromString(el, value);
  }
  function setClassesFromString(el, classString) {
    let split = (classString2) => classString2.split(" ").filter(Boolean);
    let missingClasses = (classString2) => classString2.split(" ").filter((i) => !el.classList.contains(i)).filter(Boolean);
    let addClassesAndReturnUndo = (classes) => {
      el.classList.add(...classes);
      return () => {
        el.classList.remove(...classes);
      };
    };
    classString = classString === true ? classString = "" : classString || "";
    return addClassesAndReturnUndo(missingClasses(classString));
  }
  function setClassesFromObject(el, classObject) {
    let split = (classString) => classString.split(" ").filter(Boolean);
    let forAdd = Object.entries(classObject).flatMap(([classString, bool]) => bool ? split(classString) : false).filter(Boolean);
    let forRemove = Object.entries(classObject).flatMap(([classString, bool]) => !bool ? split(classString) : false).filter(Boolean);
    let added = [];
    let removed = [];
    forRemove.forEach((i) => {
      if (el.classList.contains(i)) {
        el.classList.remove(i);
        removed.push(i);
      }
    });
    forAdd.forEach((i) => {
      if (!el.classList.contains(i)) {
        el.classList.add(i);
        added.push(i);
      }
    });
    return () => {
      removed.forEach((i) => el.classList.add(i));
      added.forEach((i) => el.classList.remove(i));
    };
  }


  function setStyles(el, value) {
    if (typeof value === "object" && value !== null) {
      return setStylesFromObject(el, value);
    }
    return setStylesFromString(el, value);
  }
  function setStylesFromObject(el, value) {
    let previousStyles = {};
    Object.entries(value).forEach(([key, value2]) => {
      previousStyles[key] = el.style[key];
      if (!key.startsWith("--")) {
        key = kebabCase(key);
      }
      el.style.setProperty(key, value2);
    });
    setTimeout(() => {
      if (el.style.length === 0) {
        el.removeAttribute("style");
      }
    });
    return () => {
      setStyles(el, previousStyles);
    };
  }
  function setStylesFromString(el, value) {
    let cache = el.getAttribute("style", value);
    el.setAttribute("style", value);
    return () => {
      el.setAttribute("style", cache || "");
    };
  }
  function kebabCase(subject) {
    return subject.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase();
  }


  function once(callback, fallback = () => {
  }) {
    let called = false;
    return function() {
      if (!called) {
        called = true;
        callback.apply(this, arguments);
      } else {
        fallback.apply(this, arguments);
      }
    };
  }


  directive("transition", (el, { value, modifiers, expression }, { evaluate: evaluate2 }) => {
    if (typeof expression === "function")
      expression = evaluate2(expression);
    if (expression === false)
      return;
    if (!expression || typeof expression === "boolean") {
      registerTransitionsFromHelper(el, modifiers, value);
    } else {
      registerTransitionsFromClassString(el, expression, value);
    }
  });
  function registerTransitionsFromClassString(el, classString, stage) {
    registerTransitionObject(el, setClasses, "");
    let directiveStorageMap = {
      "enter": (classes) => {
        el._x_transition.enter.during = classes;
      },
      "enter-start": (classes) => {
        el._x_transition.enter.start = classes;
      },
      "enter-end": (classes) => {
        el._x_transition.enter.end = classes;
      },
      "leave": (classes) => {
        el._x_transition.leave.during = classes;
      },
      "leave-start": (classes) => {
        el._x_transition.leave.start = classes;
      },
      "leave-end": (classes) => {
        el._x_transition.leave.end = classes;
      }
    };
    directiveStorageMap[stage](classString);
  }
  function registerTransitionsFromHelper(el, modifiers, stage) {
    registerTransitionObject(el, setStyles);
    let doesntSpecify = !modifiers.includes("in") && !modifiers.includes("out") && !stage;
    let transitioningIn = doesntSpecify || modifiers.includes("in") || ["enter"].includes(stage);
    let transitioningOut = doesntSpecify || modifiers.includes("out") || ["leave"].includes(stage);
    if (modifiers.includes("in") && !doesntSpecify) {
      modifiers = modifiers.filter((i, index) => index < modifiers.indexOf("out"));
    }
    if (modifiers.includes("out") && !doesntSpecify) {
      modifiers = modifiers.filter((i, index) => index > modifiers.indexOf("out"));
    }
    let wantsAll = !modifiers.includes("opacity") && !modifiers.includes("scale");
    let wantsOpacity = wantsAll || modifiers.includes("opacity");
    let wantsScale = wantsAll || modifiers.includes("scale");
    let opacityValue = wantsOpacity ? 0 : 1;
    let scaleValue = wantsScale ? modifierValue(modifiers, "scale", 95) / 100 : 1;
    let delay = modifierValue(modifiers, "delay", 0) / 1e3;
    let origin = modifierValue(modifiers, "origin", "center");
    let property = "opacity, transform";
    let durationIn = modifierValue(modifiers, "duration", 150) / 1e3;
    let durationOut = modifierValue(modifiers, "duration", 75) / 1e3;
    let easing = `cubic-bezier(0.4, 0.0, 0.2, 1)`;
    if (transitioningIn) {
      el._x_transition.enter.during = {
        transformOrigin: origin,
        transitionDelay: `${delay}s`,
        transitionProperty: property,
        transitionDuration: `${durationIn}s`,
        transitionTimingFunction: easing
      };
      el._x_transition.enter.start = {
        opacity: opacityValue,
        transform: `scale(${scaleValue})`
      };
      el._x_transition.enter.end = {
        opacity: 1,
        transform: `scale(1)`
      };
    }
    if (transitioningOut) {
      el._x_transition.leave.during = {
        transformOrigin: origin,
        transitionDelay: `${delay}s`,
        transitionProperty: property,
        transitionDuration: `${durationOut}s`,
        transitionTimingFunction: easing
      };
      el._x_transition.leave.start = {
        opacity: 1,
        transform: `scale(1)`
      };
      el._x_transition.leave.end = {
        opacity: opacityValue,
        transform: `scale(${scaleValue})`
      };
    }
  }
  function registerTransitionObject(el, setFunction, defaultValue = {}) {
    if (!el._x_transition)
      el._x_transition = {
        enter: { during: defaultValue, start: defaultValue, end: defaultValue },
        leave: { during: defaultValue, start: defaultValue, end: defaultValue },
        in(before = () => {
        }, after = () => {
        }) {
          transition(el, setFunction, {
            during: this.enter.during,
            start: this.enter.start,
            end: this.enter.end
          }, before, after);
        },
        out(before = () => {
        }, after = () => {
        }) {
          transition(el, setFunction, {
            during: this.leave.during,
            start: this.leave.start,
            end: this.leave.end
          }, before, after);
        }
      };
  }
  window.Element.prototype._x_toggleAndCascadeWithTransitions = function(el, value, show, hide) {
    const nextTick2 = document.visibilityState === "visible" ? requestAnimationFrame : setTimeout;
    let clickAwayCompatibleShow = () => nextTick2(show);
    if (value) {
      if (el._x_transition && (el._x_transition.enter || el._x_transition.leave)) {
        el._x_transition.enter && (Object.entries(el._x_transition.enter.during).length || Object.entries(el._x_transition.enter.start).length || Object.entries(el._x_transition.enter.end).length) ? el._x_transition.in(show) : clickAwayCompatibleShow();
      } else {
        el._x_transition ? el._x_transition.in(show) : clickAwayCompatibleShow();
      }
      return;
    }
    el._x_hidePromise = el._x_transition ? new Promise((resolve, reject) => {
      el._x_transition.out(() => {
      }, () => resolve(hide));
      el._x_transitioning && el._x_transitioning.beforeCancel(() => reject({ isFromCancelledTransition: true }));
    }) : Promise.resolve(hide);
    queueMicrotask(() => {
      let closest = closestHide(el);
      if (closest) {
        if (!closest._x_hideChildren)
          closest._x_hideChildren = [];
        closest._x_hideChildren.push(el);
      } else {
        nextTick2(() => {
          let hideAfterChildren = (el2) => {
            let carry = Promise.all([
              el2._x_hidePromise,
              ...(el2._x_hideChildren || []).map(hideAfterChildren)
            ]).then(([i]) => i?.());
            delete el2._x_hidePromise;
            delete el2._x_hideChildren;
            return carry;
          };
          hideAfterChildren(el).catch((e) => {
            if (!e.isFromCancelledTransition)
              throw e;
          });
        });
      }
    });
  };
  function closestHide(el) {
    let parent = el.parentNode;
    if (!parent)
      return;
    return parent._x_hidePromise ? parent : closestHide(parent);
  }
  function transition(el, setFunction, { during, start: start2, end } = {}, before = () => {
  }, after = () => {
  }) {
    if (el._x_transitioning)
      el._x_transitioning.cancel();
    if (Object.keys(during).length === 0 && Object.keys(start2).length === 0 && Object.keys(end).length === 0) {
      before();
      after();
      return;
    }
    let undoStart, undoDuring, undoEnd;
    performTransition(el, {
      start() {
        undoStart = setFunction(el, start2);
      },
      during() {
        undoDuring = setFunction(el, during);
      },
      before,
      end() {
        undoStart();
        undoEnd = setFunction(el, end);
      },
      after,
      cleanup() {
        undoDuring();
        undoEnd();
      }
    });
  }
  function performTransition(el, stages) {
    let interrupted, reachedBefore, reachedEnd;
    let finish = once(() => {
      mutateDom(() => {
        interrupted = true;
        if (!reachedBefore)
          stages.before();
        if (!reachedEnd) {
          stages.end();
          releaseNextTicks();
        }
        stages.after();
        if (el.isConnected)
          stages.cleanup();
        delete el._x_transitioning;
      });
    });
    el._x_transitioning = {
      beforeCancels: [],
      beforeCancel(callback) {
        this.beforeCancels.push(callback);
      },
      cancel: once(function() {
        while (this.beforeCancels.length) {
          this.beforeCancels.shift()();
        }
        ;
        finish();
      }),
      finish
    };
    mutateDom(() => {
      stages.start();
      stages.during();
    });
    holdNextTicks();
    requestAnimationFrame(() => {
      if (interrupted)
        return;
      let duration = Number(getComputedStyle(el).transitionDuration.replace(/,.*/, "").replace("s", "")) * 1e3;
      let delay = Number(getComputedStyle(el).transitionDelay.replace(/,.*/, "").replace("s", "")) * 1e3;
      if (duration === 0)
        duration = Number(getComputedStyle(el).animationDuration.replace("s", "")) * 1e3;
      mutateDom(() => {
        stages.before();
      });
      reachedBefore = true;
      requestAnimationFrame(() => {
        if (interrupted)
          return;
        mutateDom(() => {
          stages.end();
        });
        releaseNextTicks();
        setTimeout(el._x_transitioning.finish, duration + delay);
        reachedEnd = true;
      });
    });
  }
  function modifierValue(modifiers, key, fallback) {
    if (modifiers.indexOf(key) === -1)
      return fallback;
    const rawValue = modifiers[modifiers.indexOf(key) + 1];
    if (!rawValue)
      return fallback;
    if (key === "scale") {
      if (isNaN(rawValue))
        return fallback;
    }
    if (key === "duration" || key === "delay") {
      let match = rawValue.match(/([0-9]+)ms/);
      if (match)
        return match[1];
    }
    if (key === "origin") {
      if (["top", "right", "left", "center", "bottom"].includes(modifiers[modifiers.indexOf(key) + 2])) {
        return [rawValue, modifiers[modifiers.indexOf(key) + 2]].join(" ");
      }
    }
    return rawValue;
  }


  var isCloning = false;
  function skipDuringClone(callback, fallback = () => {
  }) {
    return (...args) => isCloning ? fallback(...args) : callback(...args);
  }
  function onlyDuringClone(callback) {
    return (...args) => isCloning && callback(...args);
  }
  var interceptors = [];
  function interceptClone(callback) {
    interceptors.push(callback);
  }
  function cloneNode(from, to) {
    interceptors.forEach((i) => i(from, to));
    isCloning = true;
    dontRegisterReactiveSideEffects(() => {
      initTree(to, (el, callback) => {
        callback(el, () => {
        });
      });
    });
    isCloning = false;
  }
  var isCloningLegacy = false;
  function clone(oldEl, newEl) {
    if (!newEl._x_dataStack)
      newEl._x_dataStack = oldEl._x_dataStack;
    isCloning = true;
    isCloningLegacy = true;
    dontRegisterReactiveSideEffects(() => {
      cloneTree(newEl);
    });
    isCloning = false;
    isCloningLegacy = false;
  }
  function cloneTree(el) {
    let hasRunThroughFirstEl = false;
    let shallowWalker = (el2, callback) => {
      walk(el2, (el3, skip) => {
        if (hasRunThroughFirstEl && isRoot(el3))
          return skip();
        hasRunThroughFirstEl = true;
        callback(el3, skip);
      });
    };
    initTree(el, shallowWalker);
  }
  function dontRegisterReactiveSideEffects(callback) {
    let cache = effect;
    overrideEffect((callback2, el) => {
      let storedEffect = cache(callback2);
      release(storedEffect);
      return () => {
      };
    });
    callback();
    overrideEffect(cache);
  }


  function bind(el, name, value, modifiers = []) {
    if (!el._x_bindings)
      el._x_bindings = reactive({});
    el._x_bindings[name] = value;
    name = modifiers.includes("camel") ? camelCase(name) : name;
    switch (name) {
      case "value":
        bindInputValue(el, value);
        break;
      case "style":
        bindStyles(el, value);
        break;
      case "class":
        bindClasses(el, value);
        break;
      case "selected":
      case "checked":
        bindAttributeAndProperty(el, name, value);
        break;
      default:
        bindAttribute(el, name, value);
        break;
    }
  }
  function bindInputValue(el, value) {
    if (isRadio(el)) {
      if (el.attributes.value === void 0) {
        el.value = value;
      }
      if (window.fromModel) {
        if (typeof value === "boolean") {
          el.checked = safeParseBoolean(el.value) === value;
        } else {
          el.checked = checkedAttrLooseCompare(el.value, value);
        }
      }
    } else if (isCheckbox(el)) {
      if (Number.isInteger(value)) {
        el.value = value;
      } else if (!Array.isArray(value) && typeof value !== "boolean" && ![null, void 0].includes(value)) {
        el.value = String(value);
      } else {
        if (Array.isArray(value)) {
          el.checked = value.some((val) => checkedAttrLooseCompare(val, el.value));
        } else {
          el.checked = !!value;
        }
      }
    } else if (el.tagName === "SELECT") {
      updateSelect(el, value);
    } else {
      if (el.value === value)
        return;
      el.value = value === void 0 ? "" : value;
    }
  }
  function bindClasses(el, value) {
    if (el._x_undoAddedClasses)
      el._x_undoAddedClasses();
    el._x_undoAddedClasses = setClasses(el, value);
  }
  function bindStyles(el, value) {
    if (el._x_undoAddedStyles)
      el._x_undoAddedStyles();
    el._x_undoAddedStyles = setStyles(el, value);
  }
  function bindAttributeAndProperty(el, name, value) {
    bindAttribute(el, name, value);
    setPropertyIfChanged(el, name, value);
  }
  function bindAttribute(el, name, value) {
    if ([null, void 0, false].includes(value) && attributeShouldntBePreservedIfFalsy(name)) {
      el.removeAttribute(name);
    } else {
      if (isBooleanAttr(name))
        value = name;
      setIfChanged(el, name, value);
    }
  }
  function setIfChanged(el, attrName, value) {
    if (el.getAttribute(attrName) != value) {
      el.setAttribute(attrName, value);
    }
  }
  function setPropertyIfChanged(el, propName, value) {
    if (el[propName] !== value) {
      el[propName] = value;
    }
  }
  function updateSelect(el, value) {
    const arrayWrappedValue = [].concat(value).map((value2) => {
      return value2 + "";
    });
    Array.from(el.options).forEach((option) => {
      option.selected = arrayWrappedValue.includes(option.value);
    });
  }
  function camelCase(subject) {
    return subject.toLowerCase().replace(/-(\w)/g, (match, char) => char.toUpperCase());
  }
  function checkedAttrLooseCompare(valueA, valueB) {
    return valueA == valueB;
  }
  function safeParseBoolean(rawValue) {
    if ([1, "1", "true", "on", "yes", true].includes(rawValue)) {
      return true;
    }
    if ([0, "0", "false", "off", "no", false].includes(rawValue)) {
      return false;
    }
    return rawValue ? Boolean(rawValue) : null;
  }
  var booleanAttributes =  new Set([
    "allowfullscreen",
    "async",
    "autofocus",
    "autoplay",
    "checked",
    "controls",
    "default",
    "defer",
    "disabled",
    "formnovalidate",
    "inert",
    "ismap",
    "itemscope",
    "loop",
    "multiple",
    "muted",
    "nomodule",
    "novalidate",
    "open",
    "playsinline",
    "readonly",
    "required",
    "reversed",
    "selected",
    "shadowrootclonable",
    "shadowrootdelegatesfocus",
    "shadowrootserializable"
  ]);
  function isBooleanAttr(attrName) {
    return booleanAttributes.has(attrName);
  }
  function attributeShouldntBePreservedIfFalsy(name) {
    return !["aria-pressed", "aria-checked", "aria-expanded", "aria-selected"].includes(name);
  }
  function getBinding(el, name, fallback) {
    if (el._x_bindings && el._x_bindings[name] !== void 0)
      return el._x_bindings[name];
    return getAttributeBinding(el, name, fallback);
  }
  function extractProp(el, name, fallback, extract = true) {
    if (el._x_bindings && el._x_bindings[name] !== void 0)
      return el._x_bindings[name];
    if (el._x_inlineBindings && el._x_inlineBindings[name] !== void 0) {
      let binding = el._x_inlineBindings[name];
      binding.extract = extract;
      return dontAutoEvaluateFunctions(() => {
        return evaluate(el, binding.expression);
      });
    }
    return getAttributeBinding(el, name, fallback);
  }
  function getAttributeBinding(el, name, fallback) {
    let attr = el.getAttribute(name);
    if (attr === null)
      return typeof fallback === "function" ? fallback() : fallback;
    if (attr === "")
      return true;
    if (isBooleanAttr(name)) {
      return !![name, "true"].includes(attr);
    }
    return attr;
  }
  function isCheckbox(el) {
    return el.type === "checkbox" || el.localName === "ui-checkbox" || el.localName === "ui-switch";
  }
  function isRadio(el) {
    return el.type === "radio" || el.localName === "ui-radio";
  }


  function debounce(func, wait) {
    var timeout;
    return function() {
      var context = this, args = arguments;
      var later = function() {
        timeout = null;
        func.apply(context, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }


  function throttle(func, limit) {
    let inThrottle;
    return function() {
      let context = this, args = arguments;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }


  function entangle({ get: outerGet, set: outerSet }, { get: innerGet, set: innerSet }) {
    let firstRun = true;
    let outerHash;
    let innerHash;
    let reference = effect(() => {
      let outer = outerGet();
      let inner = innerGet();
      if (firstRun) {
        innerSet(cloneIfObject(outer));
        firstRun = false;
      } else {
        let outerHashLatest = JSON.stringify(outer);
        let innerHashLatest = JSON.stringify(inner);
        if (outerHashLatest !== outerHash) {
          innerSet(cloneIfObject(outer));
        } else if (outerHashLatest !== innerHashLatest) {
          outerSet(cloneIfObject(inner));
        } else {
        }
      }
      outerHash = JSON.stringify(outerGet());
      innerHash = JSON.stringify(innerGet());
    });
    return () => {
      release(reference);
    };
  }
  function cloneIfObject(value) {
    return typeof value === "object" ? JSON.parse(JSON.stringify(value)) : value;
  }


  function plugin(callback) {
    let callbacks = Array.isArray(callback) ? callback : [callback];
    callbacks.forEach((i) => i(alpine_default));
  }


  var stores = {};
  var isReactive = false;
  function store(name, value) {
    if (!isReactive) {
      stores = reactive(stores);
      isReactive = true;
    }
    if (value === void 0) {
      return stores[name];
    }
    stores[name] = value;
    initInterceptors(stores[name]);
    if (typeof value === "object" && value !== null && value.hasOwnProperty("init") && typeof value.init === "function") {
      stores[name].init();
    }
  }
  function getStores() {
    return stores;
  }


  var binds = {};
  function bind2(name, bindings) {
    let getBindings = typeof bindings !== "function" ? () => bindings : bindings;
    if (name instanceof Element) {
      return applyBindingsObject(name, getBindings());
    } else {
      binds[name] = getBindings;
    }
    return () => {
    };
  }
  function injectBindingProviders(obj) {
    Object.entries(binds).forEach(([name, callback]) => {
      Object.defineProperty(obj, name, {
        get() {
          return (...args) => {
            return callback(...args);
          };
        }
      });
    });
    return obj;
  }
  function applyBindingsObject(el, obj, original) {
    let cleanupRunners = [];
    while (cleanupRunners.length)
      cleanupRunners.pop()();
    let attributes = Object.entries(obj).map(([name, value]) => ({ name, value }));
    let staticAttributes = attributesOnly(attributes);
    attributes = attributes.map((attribute) => {
      if (staticAttributes.find((attr) => attr.name === attribute.name)) {
        return {
          name: `x-bind:${attribute.name}`,
          value: `"${attribute.value}"`
        };
      }
      return attribute;
    });
    directives(el, attributes, original).map((handle) => {
      cleanupRunners.push(handle.runCleanups);
      handle();
    });
    return () => {
      while (cleanupRunners.length)
        cleanupRunners.pop()();
    };
  }


  var datas = {};
  function data(name, callback) {
    datas[name] = callback;
  }
  function injectDataProviders(obj, context) {
    Object.entries(datas).forEach(([name, callback]) => {
      Object.defineProperty(obj, name, {
        get() {
          return (...args) => {
            return callback.bind(context)(...args);
          };
        },
        enumerable: false
      });
    });
    return obj;
  }


  var Alpine = {
    get reactive() {
      return reactive;
    },
    get release() {
      return release;
    },
    get effect() {
      return effect;
    },
    get raw() {
      return raw;
    },
    version: "3.14.8",
    flushAndStopDeferringMutations,
    dontAutoEvaluateFunctions,
    disableEffectScheduling,
    startObservingMutations,
    stopObservingMutations,
    setReactivityEngine,
    onAttributeRemoved,
    onAttributesAdded,
    closestDataStack,
    skipDuringClone,
    onlyDuringClone,
    addRootSelector,
    addInitSelector,
    interceptClone,
    addScopeToNode,
    deferMutations,
    mapAttributes,
    evaluateLater,
    interceptInit,
    setEvaluator,
    mergeProxies,
    extractProp,
    findClosest,
    onElRemoved,
    closestRoot,
    destroyTree,
    interceptor,

    transition,

    setStyles,

    mutateDom,
    directive,
    entangle,
    throttle,
    debounce,
    evaluate,
    initTree,
    nextTick,
    prefixed: prefix,
    prefix: setPrefix,
    plugin,
    magic,
    store,
    start,
    clone,

    cloneNode,

    bound: getBinding,
    $data: scope,
    watch,
    walk,
    data,
    bind: bind2
  };
  var alpine_default = Alpine;


  function makeMap(str, expectsLowerCase) {
    const map =  Object.create(null);
    const list = str.split(",");
    for (let i = 0; i < list.length; i++) {
      map[list[i]] = true;
    }
    return expectsLowerCase ? (val) => !!map[val.toLowerCase()] : (val) => !!map[val];
  }
  var specialBooleanAttrs = `itemscope,allowfullscreen,formnovalidate,ismap,nomodule,novalidate,readonly`;
  var isBooleanAttr2 =  makeMap(specialBooleanAttrs + `,async,autofocus,autoplay,controls,default,defer,disabled,hidden,loop,open,required,reversed,scoped,seamless,checked,muted,multiple,selected`);
  var EMPTY_OBJ = true ? Object.freeze({}) : {};
  var EMPTY_ARR = true ? Object.freeze([]) : [];
  var hasOwnProperty = Object.prototype.hasOwnProperty;
  var hasOwn = (val, key) => hasOwnProperty.call(val, key);
  var isArray = Array.isArray;
  var isMap = (val) => toTypeString(val) === "[object Map]";
  var isString = (val) => typeof val === "string";
  var isSymbol = (val) => typeof val === "symbol";
  var isObject = (val) => val !== null && typeof val === "object";
  var objectToString = Object.prototype.toString;
  var toTypeString = (value) => objectToString.call(value);
  var toRawType = (value) => {
    return toTypeString(value).slice(8, -1);
  };
  var isIntegerKey = (key) => isString(key) && key !== "NaN" && key[0] !== "-" && "" + parseInt(key, 10) === key;
  var cacheStringFunction = (fn) => {
    const cache =  Object.create(null);
    return (str) => {
      const hit = cache[str];
      return hit || (cache[str] = fn(str));
    };
  };
  var camelizeRE = /-(\w)/g;
  var camelize = cacheStringFunction((str) => {
    return str.replace(camelizeRE, (_, c) => c ? c.toUpperCase() : "");
  });
  var hyphenateRE = /\B([A-Z])/g;
  var hyphenate = cacheStringFunction((str) => str.replace(hyphenateRE, "-$1").toLowerCase());
  var capitalize = cacheStringFunction((str) => str.charAt(0).toUpperCase() + str.slice(1));
  var toHandlerKey = cacheStringFunction((str) => str ? `on${capitalize(str)}` : ``);
  var hasChanged = (value, oldValue) => value !== oldValue && (value === value || oldValue === oldValue);


  var targetMap =  new WeakMap();
  var effectStack = [];
  var activeEffect;
  var ITERATE_KEY = Symbol(true ? "iterate" : "");
  var MAP_KEY_ITERATE_KEY = Symbol(true ? "Map key iterate" : "");
  function isEffect(fn) {
    return fn && fn._isEffect === true;
  }
  function effect2(fn, options = EMPTY_OBJ) {
    if (isEffect(fn)) {
      fn = fn.raw;
    }
    const effect3 = createReactiveEffect(fn, options);
    if (!options.lazy) {
      effect3();
    }
    return effect3;
  }
  function stop(effect3) {
    if (effect3.active) {
      cleanup(effect3);
      if (effect3.options.onStop) {
        effect3.options.onStop();
      }
      effect3.active = false;
    }
  }
  var uid = 0;
  function createReactiveEffect(fn, options) {
    const effect3 = function reactiveEffect() {
      if (!effect3.active) {
        return fn();
      }
      if (!effectStack.includes(effect3)) {
        cleanup(effect3);
        try {
          enableTracking();
          effectStack.push(effect3);
          activeEffect = effect3;
          return fn();
        } finally {
          effectStack.pop();
          resetTracking();
          activeEffect = effectStack[effectStack.length - 1];
        }
      }
    };
    effect3.id = uid++;
    effect3.allowRecurse = !!options.allowRecurse;
    effect3._isEffect = true;
    effect3.active = true;
    effect3.raw = fn;
    effect3.deps = [];
    effect3.options = options;
    return effect3;
  }
  function cleanup(effect3) {
    const { deps } = effect3;
    if (deps.length) {
      for (let i = 0; i < deps.length; i++) {
        deps[i].delete(effect3);
      }
      deps.length = 0;
    }
  }
  var shouldTrack = true;
  var trackStack = [];
  function pauseTracking() {
    trackStack.push(shouldTrack);
    shouldTrack = false;
  }
  function enableTracking() {
    trackStack.push(shouldTrack);
    shouldTrack = true;
  }
  function resetTracking() {
    const last = trackStack.pop();
    shouldTrack = last === void 0 ? true : last;
  }
  function track(target, type, key) {
    if (!shouldTrack || activeEffect === void 0) {
      return;
    }
    let depsMap = targetMap.get(target);
    if (!depsMap) {
      targetMap.set(target, depsMap =  new Map());
    }
    let dep = depsMap.get(key);
    if (!dep) {
      depsMap.set(key, dep =  new Set());
    }
    if (!dep.has(activeEffect)) {
      dep.add(activeEffect);
      activeEffect.deps.push(dep);
      if (activeEffect.options.onTrack) {
        activeEffect.options.onTrack({
          effect: activeEffect,
          target,
          type,
          key
        });
      }
    }
  }
  function trigger(target, type, key, newValue, oldValue, oldTarget) {
    const depsMap = targetMap.get(target);
    if (!depsMap) {
      return;
    }
    const effects =  new Set();
    const add2 = (effectsToAdd) => {
      if (effectsToAdd) {
        effectsToAdd.forEach((effect3) => {
          if (effect3 !== activeEffect || effect3.allowRecurse) {
            effects.add(effect3);
          }
        });
      }
    };
    if (type === "clear") {
      depsMap.forEach(add2);
    } else if (key === "length" && isArray(target)) {
      depsMap.forEach((dep, key2) => {
        if (key2 === "length" || key2 >= newValue) {
          add2(dep);
        }
      });
    } else {
      if (key !== void 0) {
        add2(depsMap.get(key));
      }
      switch (type) {
        case "add":
          if (!isArray(target)) {
            add2(depsMap.get(ITERATE_KEY));
            if (isMap(target)) {
              add2(depsMap.get(MAP_KEY_ITERATE_KEY));
            }
          } else if (isIntegerKey(key)) {
            add2(depsMap.get("length"));
          }
          break;
        case "delete":
          if (!isArray(target)) {
            add2(depsMap.get(ITERATE_KEY));
            if (isMap(target)) {
              add2(depsMap.get(MAP_KEY_ITERATE_KEY));
            }
          }
          break;
        case "set":
          if (isMap(target)) {
            add2(depsMap.get(ITERATE_KEY));
          }
          break;
      }
    }
    const run = (effect3) => {
      if (effect3.options.onTrigger) {
        effect3.options.onTrigger({
          effect: effect3,
          target,
          key,
          type,
          newValue,
          oldValue,
          oldTarget
        });
      }
      if (effect3.options.scheduler) {
        effect3.options.scheduler(effect3);
      } else {
        effect3();
      }
    };
    effects.forEach(run);
  }
  var isNonTrackableKeys =  makeMap(`__proto__,__v_isRef,__isVue`);
  var builtInSymbols = new Set(Object.getOwnPropertyNames(Symbol).map((key) => Symbol[key]).filter(isSymbol));
  var get2 =  createGetter();
  var readonlyGet =  createGetter(true);
  var arrayInstrumentations =  createArrayInstrumentations();
  function createArrayInstrumentations() {
    const instrumentations = {};
    ["includes", "indexOf", "lastIndexOf"].forEach((key) => {
      instrumentations[key] = function(...args) {
        const arr = toRaw(this);
        for (let i = 0, l = this.length; i < l; i++) {
          track(arr, "get", i + "");
        }
        const res = arr[key](...args);
        if (res === -1 || res === false) {
          return arr[key](...args.map(toRaw));
        } else {
          return res;
        }
      };
    });
    ["push", "pop", "shift", "unshift", "splice"].forEach((key) => {
      instrumentations[key] = function(...args) {
        pauseTracking();
        const res = toRaw(this)[key].apply(this, args);
        resetTracking();
        return res;
      };
    });
    return instrumentations;
  }
  function createGetter(isReadonly = false, shallow = false) {
    return function get3(target, key, receiver) {
      if (key === "__v_isReactive") {
        return !isReadonly;
      } else if (key === "__v_isReadonly") {
        return isReadonly;
      } else if (key === "__v_raw" && receiver === (isReadonly ? shallow ? shallowReadonlyMap : readonlyMap : shallow ? shallowReactiveMap : reactiveMap).get(target)) {
        return target;
      }
      const targetIsArray = isArray(target);
      if (!isReadonly && targetIsArray && hasOwn(arrayInstrumentations, key)) {
        return Reflect.get(arrayInstrumentations, key, receiver);
      }
      const res = Reflect.get(target, key, receiver);
      if (isSymbol(key) ? builtInSymbols.has(key) : isNonTrackableKeys(key)) {
        return res;
      }
      if (!isReadonly) {
        track(target, "get", key);
      }
      if (shallow) {
        return res;
      }
      if (isRef(res)) {
        const shouldUnwrap = !targetIsArray || !isIntegerKey(key);
        return shouldUnwrap ? res.value : res;
      }
      if (isObject(res)) {
        return isReadonly ? readonly(res) : reactive2(res);
      }
      return res;
    };
  }
  var set2 =  createSetter();
  function createSetter(shallow = false) {
    return function set3(target, key, value, receiver) {
      let oldValue = target[key];
      if (!shallow) {
        value = toRaw(value);
        oldValue = toRaw(oldValue);
        if (!isArray(target) && isRef(oldValue) && !isRef(value)) {
          oldValue.value = value;
          return true;
        }
      }
      const hadKey = isArray(target) && isIntegerKey(key) ? Number(key) < target.length : hasOwn(target, key);
      const result = Reflect.set(target, key, value, receiver);
      if (target === toRaw(receiver)) {
        if (!hadKey) {
          trigger(target, "add", key, value);
        } else if (hasChanged(value, oldValue)) {
          trigger(target, "set", key, value, oldValue);
        }
      }
      return result;
    };
  }
  function deleteProperty(target, key) {
    const hadKey = hasOwn(target, key);
    const oldValue = target[key];
    const result = Reflect.deleteProperty(target, key);
    if (result && hadKey) {
      trigger(target, "delete", key, void 0, oldValue);
    }
    return result;
  }
  function has(target, key) {
    const result = Reflect.has(target, key);
    if (!isSymbol(key) || !builtInSymbols.has(key)) {
      track(target, "has", key);
    }
    return result;
  }
  function ownKeys(target) {
    track(target, "iterate", isArray(target) ? "length" : ITERATE_KEY);
    return Reflect.ownKeys(target);
  }
  var mutableHandlers = {
    get: get2,
    set: set2,
    deleteProperty,
    has,
    ownKeys
  };
  var readonlyHandlers = {
    get: readonlyGet,
    set(target, key) {
      if (true) {
        console.warn(`Set operation on key "${String(key)}" failed: target is readonly.`, target);
      }
      return true;
    },
    deleteProperty(target, key) {
      if (true) {
        console.warn(`Delete operation on key "${String(key)}" failed: target is readonly.`, target);
      }
      return true;
    }
  };
  var toReactive = (value) => isObject(value) ? reactive2(value) : value;
  var toReadonly = (value) => isObject(value) ? readonly(value) : value;
  var toShallow = (value) => value;
  var getProto = (v) => Reflect.getPrototypeOf(v);
  function get$1(target, key, isReadonly = false, isShallow = false) {
    target = target[
      "__v_raw"

    ];
    const rawTarget = toRaw(target);
    const rawKey = toRaw(key);
    if (key !== rawKey) {
      !isReadonly && track(rawTarget, "get", key);
    }
    !isReadonly && track(rawTarget, "get", rawKey);
    const { has: has2 } = getProto(rawTarget);
    const wrap = isShallow ? toShallow : isReadonly ? toReadonly : toReactive;
    if (has2.call(rawTarget, key)) {
      return wrap(target.get(key));
    } else if (has2.call(rawTarget, rawKey)) {
      return wrap(target.get(rawKey));
    } else if (target !== rawTarget) {
      target.get(key);
    }
  }
  function has$1(key, isReadonly = false) {
    const target = this[
      "__v_raw"

    ];
    const rawTarget = toRaw(target);
    const rawKey = toRaw(key);
    if (key !== rawKey) {
      !isReadonly && track(rawTarget, "has", key);
    }
    !isReadonly && track(rawTarget, "has", rawKey);
    return key === rawKey ? target.has(key) : target.has(key) || target.has(rawKey);
  }
  function size(target, isReadonly = false) {
    target = target[
      "__v_raw"

    ];
    !isReadonly && track(toRaw(target), "iterate", ITERATE_KEY);
    return Reflect.get(target, "size", target);
  }
  function add(value) {
    value = toRaw(value);
    const target = toRaw(this);
    const proto = getProto(target);
    const hadKey = proto.has.call(target, value);
    if (!hadKey) {
      target.add(value);
      trigger(target, "add", value, value);
    }
    return this;
  }
  function set$1(key, value) {
    value = toRaw(value);
    const target = toRaw(this);
    const { has: has2, get: get3 } = getProto(target);
    let hadKey = has2.call(target, key);
    if (!hadKey) {
      key = toRaw(key);
      hadKey = has2.call(target, key);
    } else if (true) {
      checkIdentityKeys(target, has2, key);
    }
    const oldValue = get3.call(target, key);
    target.set(key, value);
    if (!hadKey) {
      trigger(target, "add", key, value);
    } else if (hasChanged(value, oldValue)) {
      trigger(target, "set", key, value, oldValue);
    }
    return this;
  }
  function deleteEntry(key) {
    const target = toRaw(this);
    const { has: has2, get: get3 } = getProto(target);
    let hadKey = has2.call(target, key);
    if (!hadKey) {
      key = toRaw(key);
      hadKey = has2.call(target, key);
    } else if (true) {
      checkIdentityKeys(target, has2, key);
    }
    const oldValue = get3 ? get3.call(target, key) : void 0;
    const result = target.delete(key);
    if (hadKey) {
      trigger(target, "delete", key, void 0, oldValue);
    }
    return result;
  }
  function clear() {
    const target = toRaw(this);
    const hadItems = target.size !== 0;
    const oldTarget = true ? isMap(target) ? new Map(target) : new Set(target) : void 0;
    const result = target.clear();
    if (hadItems) {
      trigger(target, "clear", void 0, void 0, oldTarget);
    }
    return result;
  }
  function createForEach(isReadonly, isShallow) {
    return function forEach(callback, thisArg) {
      const observed = this;
      const target = observed[
        "__v_raw"

      ];
      const rawTarget = toRaw(target);
      const wrap = isShallow ? toShallow : isReadonly ? toReadonly : toReactive;
      !isReadonly && track(rawTarget, "iterate", ITERATE_KEY);
      return target.forEach((value, key) => {
        return callback.call(thisArg, wrap(value), wrap(key), observed);
      });
    };
  }
  function createIterableMethod(method, isReadonly, isShallow) {
    return function(...args) {
      const target = this[
        "__v_raw"

      ];
      const rawTarget = toRaw(target);
      const targetIsMap = isMap(rawTarget);
      const isPair = method === "entries" || method === Symbol.iterator && targetIsMap;
      const isKeyOnly = method === "keys" && targetIsMap;
      const innerIterator = target[method](...args);
      const wrap = isShallow ? toShallow : isReadonly ? toReadonly : toReactive;
      !isReadonly && track(rawTarget, "iterate", isKeyOnly ? MAP_KEY_ITERATE_KEY : ITERATE_KEY);
      return {

        next() {
          const { value, done } = innerIterator.next();
          return done ? { value, done } : {
            value: isPair ? [wrap(value[0]), wrap(value[1])] : wrap(value),
            done
          };
        },

        [Symbol.iterator]() {
          return this;
        }
      };
    };
  }
  function createReadonlyMethod(type) {
    return function(...args) {
      if (true) {
        const key = args[0] ? `on key "${args[0]}" ` : ``;
        console.warn(`${capitalize(type)} operation ${key}failed: target is readonly.`, toRaw(this));
      }
      return type === "delete" ? false : this;
    };
  }
  function createInstrumentations() {
    const mutableInstrumentations2 = {
      get(key) {
        return get$1(this, key);
      },
      get size() {
        return size(this);
      },
      has: has$1,
      add,
      set: set$1,
      delete: deleteEntry,
      clear,
      forEach: createForEach(false, false)
    };
    const shallowInstrumentations2 = {
      get(key) {
        return get$1(this, key, false, true);
      },
      get size() {
        return size(this);
      },
      has: has$1,
      add,
      set: set$1,
      delete: deleteEntry,
      clear,
      forEach: createForEach(false, true)
    };
    const readonlyInstrumentations2 = {
      get(key) {
        return get$1(this, key, true);
      },
      get size() {
        return size(this, true);
      },
      has(key) {
        return has$1.call(this, key, true);
      },
      add: createReadonlyMethod(
        "add"

      ),
      set: createReadonlyMethod(
        "set"

      ),
      delete: createReadonlyMethod(
        "delete"

      ),
      clear: createReadonlyMethod(
        "clear"

      ),
      forEach: createForEach(true, false)
    };
    const shallowReadonlyInstrumentations2 = {
      get(key) {
        return get$1(this, key, true, true);
      },
      get size() {
        return size(this, true);
      },
      has(key) {
        return has$1.call(this, key, true);
      },
      add: createReadonlyMethod(
        "add"

      ),
      set: createReadonlyMethod(
        "set"

      ),
      delete: createReadonlyMethod(
        "delete"

      ),
      clear: createReadonlyMethod(
        "clear"

      ),
      forEach: createForEach(true, true)
    };
    const iteratorMethods = ["keys", "values", "entries", Symbol.iterator];
    iteratorMethods.forEach((method) => {
      mutableInstrumentations2[method] = createIterableMethod(method, false, false);
      readonlyInstrumentations2[method] = createIterableMethod(method, true, false);
      shallowInstrumentations2[method] = createIterableMethod(method, false, true);
      shallowReadonlyInstrumentations2[method] = createIterableMethod(method, true, true);
    });
    return [
      mutableInstrumentations2,
      readonlyInstrumentations2,
      shallowInstrumentations2,
      shallowReadonlyInstrumentations2
    ];
  }
  var [mutableInstrumentations, readonlyInstrumentations, shallowInstrumentations, shallowReadonlyInstrumentations] =  createInstrumentations();
  function createInstrumentationGetter(isReadonly, shallow) {
    const instrumentations = shallow ? isReadonly ? shallowReadonlyInstrumentations : shallowInstrumentations : isReadonly ? readonlyInstrumentations : mutableInstrumentations;
    return (target, key, receiver) => {
      if (key === "__v_isReactive") {
        return !isReadonly;
      } else if (key === "__v_isReadonly") {
        return isReadonly;
      } else if (key === "__v_raw") {
        return target;
      }
      return Reflect.get(hasOwn(instrumentations, key) && key in target ? instrumentations : target, key, receiver);
    };
  }
  var mutableCollectionHandlers = {
    get:  createInstrumentationGetter(false, false)
  };
  var readonlyCollectionHandlers = {
    get:  createInstrumentationGetter(true, false)
  };
  function checkIdentityKeys(target, has2, key) {
    const rawKey = toRaw(key);
    if (rawKey !== key && has2.call(target, rawKey)) {
      const type = toRawType(target);
      console.warn(`Reactive ${type} contains both the raw and reactive versions of the same object${type === `Map` ? ` as keys` : ``}, which can lead to inconsistencies. Avoid differentiating between the raw and reactive versions of an object and only use the reactive version if possible.`);
    }
  }
  var reactiveMap =  new WeakMap();
  var shallowReactiveMap =  new WeakMap();
  var readonlyMap =  new WeakMap();
  var shallowReadonlyMap =  new WeakMap();
  function targetTypeMap(rawType) {
    switch (rawType) {
      case "Object":
      case "Array":
        return 1;
      case "Map":
      case "Set":
      case "WeakMap":
      case "WeakSet":
        return 2;
      default:
        return 0;
    }
  }
  function getTargetType(value) {
    return value[
      "__v_skip"

    ] || !Object.isExtensible(value) ? 0 : targetTypeMap(toRawType(value));
  }
  function reactive2(target) {
    if (target && target[
      "__v_isReadonly"

    ]) {
      return target;
    }
    return createReactiveObject(target, false, mutableHandlers, mutableCollectionHandlers, reactiveMap);
  }
  function readonly(target) {
    return createReactiveObject(target, true, readonlyHandlers, readonlyCollectionHandlers, readonlyMap);
  }
  function createReactiveObject(target, isReadonly, baseHandlers, collectionHandlers, proxyMap) {
    if (!isObject(target)) {
      if (true) {
        console.warn(`value cannot be made reactive: ${String(target)}`);
      }
      return target;
    }
    if (target[
      "__v_raw"

    ] && !(isReadonly && target[
      "__v_isReactive"

    ])) {
      return target;
    }
    const existingProxy = proxyMap.get(target);
    if (existingProxy) {
      return existingProxy;
    }
    const targetType = getTargetType(target);
    if (targetType === 0) {
      return target;
    }
    const proxy = new Proxy(target, targetType === 2 ? collectionHandlers : baseHandlers);
    proxyMap.set(target, proxy);
    return proxy;
  }
  function toRaw(observed) {
    return observed && toRaw(observed[
      "__v_raw"

    ]) || observed;
  }
  function isRef(r) {
    return Boolean(r && r.__v_isRef === true);
  }


  magic("nextTick", () => nextTick);


  magic("dispatch", (el) => dispatch.bind(dispatch, el));


  magic("watch", (el, { evaluateLater: evaluateLater2, cleanup: cleanup2 }) => (key, callback) => {
    let evaluate2 = evaluateLater2(key);
    let getter = () => {
      let value;
      evaluate2((i) => value = i);
      return value;
    };
    let unwatch = watch(getter, callback);
    cleanup2(unwatch);
  });


  magic("store", getStores);


  magic("data", (el) => scope(el));


  magic("root", (el) => closestRoot(el));


  magic("refs", (el) => {
    if (el._x_refs_proxy)
      return el._x_refs_proxy;
    el._x_refs_proxy = mergeProxies(getArrayOfRefObject(el));
    return el._x_refs_proxy;
  });
  function getArrayOfRefObject(el) {
    let refObjects = [];
    findClosest(el, (i) => {
      if (i._x_refs)
        refObjects.push(i._x_refs);
    });
    return refObjects;
  }


  var globalIdMemo = {};
  function findAndIncrementId(name) {
    if (!globalIdMemo[name])
      globalIdMemo[name] = 0;
    return ++globalIdMemo[name];
  }
  function closestIdRoot(el, name) {
    return findClosest(el, (element) => {
      if (element._x_ids && element._x_ids[name])
        return true;
    });
  }
  function setIdRoot(el, name) {
    if (!el._x_ids)
      el._x_ids = {};
    if (!el._x_ids[name])
      el._x_ids[name] = findAndIncrementId(name);
  }


  magic("id", (el, { cleanup: cleanup2 }) => (name, key = null) => {
    let cacheKey = `${name}${key ? `-${key}` : ""}`;
    return cacheIdByNameOnElement(el, cacheKey, cleanup2, () => {
      let root = closestIdRoot(el, name);
      let id = root ? root._x_ids[name] : findAndIncrementId(name);
      return key ? `${name}-${id}-${key}` : `${name}-${id}`;
    });
  });
  interceptClone((from, to) => {
    if (from._x_id) {
      to._x_id = from._x_id;
    }
  });
  function cacheIdByNameOnElement(el, cacheKey, cleanup2, callback) {
    if (!el._x_id)
      el._x_id = {};
    if (el._x_id[cacheKey])
      return el._x_id[cacheKey];
    let output = callback();
    el._x_id[cacheKey] = output;
    cleanup2(() => {
      delete el._x_id[cacheKey];
    });
    return output;
  }


  magic("el", (el) => el);


  warnMissingPluginMagic("Focus", "focus", "focus");
  warnMissingPluginMagic("Persist", "persist", "persist");
  function warnMissingPluginMagic(name, magicName, slug) {
    magic(magicName, (el) => warn(`You can't use [$${magicName}] without first installing the "${name}" plugin here: https://alpinejs.dev/plugins/${slug}`, el));
  }


  directive("modelable", (el, { expression }, { effect: effect3, evaluateLater: evaluateLater2, cleanup: cleanup2 }) => {
    let func = evaluateLater2(expression);
    let innerGet = () => {
      let result;
      func((i) => result = i);
      return result;
    };
    let evaluateInnerSet = evaluateLater2(`${expression} = __placeholder`);
    let innerSet = (val) => evaluateInnerSet(() => {
    }, { scope: { "__placeholder": val } });
    let initialValue = innerGet();
    innerSet(initialValue);
    queueMicrotask(() => {
      if (!el._x_model)
        return;
      el._x_removeModelListeners["default"]();
      let outerGet = el._x_model.get;
      let outerSet = el._x_model.set;
      let releaseEntanglement = entangle(
        {
          get() {
            return outerGet();
          },
          set(value) {
            outerSet(value);
          }
        },
        {
          get() {
            return innerGet();
          },
          set(value) {
            innerSet(value);
          }
        }
      );
      cleanup2(releaseEntanglement);
    });
  });


  directive("teleport", (el, { modifiers, expression }, { cleanup: cleanup2 }) => {
    if (el.tagName.toLowerCase() !== "template")
      warn("x-teleport can only be used on a <template> tag", el);
    let target = getTarget(expression);
    let clone2 = el.content.cloneNode(true).firstElementChild;
    el._x_teleport = clone2;
    clone2._x_teleportBack = el;
    el.setAttribute("data-teleport-template", true);
    clone2.setAttribute("data-teleport-target", true);
    if (el._x_forwardEvents) {
      el._x_forwardEvents.forEach((eventName) => {
        clone2.addEventListener(eventName, (e) => {
          e.stopPropagation();
          el.dispatchEvent(new e.constructor(e.type, e));
        });
      });
    }
    addScopeToNode(clone2, {}, el);
    let placeInDom = (clone3, target2, modifiers2) => {
      if (modifiers2.includes("prepend")) {
        target2.parentNode.insertBefore(clone3, target2);
      } else if (modifiers2.includes("append")) {
        target2.parentNode.insertBefore(clone3, target2.nextSibling);
      } else {
        target2.appendChild(clone3);
      }
    };
    mutateDom(() => {
      placeInDom(clone2, target, modifiers);
      skipDuringClone(() => {
        initTree(clone2);
      })();
    });
    el._x_teleportPutBack = () => {
      let target2 = getTarget(expression);
      mutateDom(() => {
        placeInDom(el._x_teleport, target2, modifiers);
      });
    };
    cleanup2(
      () => mutateDom(() => {
        clone2.remove();
        destroyTree(clone2);
      })
    );
  });
  var teleportContainerDuringClone = document.createElement("div");
  function getTarget(expression) {
    let target = skipDuringClone(() => {
      return document.querySelector(expression);
    }, () => {
      return teleportContainerDuringClone;
    })();
    if (!target)
      warn(`Cannot find x-teleport element for selector: "${expression}"`);
    return target;
  }


  var handler = () => {
  };
  handler.inline = (el, { modifiers }, { cleanup: cleanup2 }) => {
    modifiers.includes("self") ? el._x_ignoreSelf = true : el._x_ignore = true;
    cleanup2(() => {
      modifiers.includes("self") ? delete el._x_ignoreSelf : delete el._x_ignore;
    });
  };
  directive("ignore", handler);


  directive("effect", skipDuringClone((el, { expression }, { effect: effect3 }) => {
    effect3(evaluateLater(el, expression));
  }));


  function on(el, event, modifiers, callback) {
    let listenerTarget = el;
    let handler4 = (e) => callback(e);
    let options = {};
    let wrapHandler = (callback2, wrapper) => (e) => wrapper(callback2, e);
    if (modifiers.includes("dot"))
      event = dotSyntax(event);
    if (modifiers.includes("camel"))
      event = camelCase2(event);
    if (modifiers.includes("passive"))
      options.passive = true;
    if (modifiers.includes("capture"))
      options.capture = true;
    if (modifiers.includes("window"))
      listenerTarget = window;
    if (modifiers.includes("document"))
      listenerTarget = document;
    if (modifiers.includes("debounce")) {
      let nextModifier = modifiers[modifiers.indexOf("debounce") + 1] || "invalid-wait";
      let wait = isNumeric(nextModifier.split("ms")[0]) ? Number(nextModifier.split("ms")[0]) : 250;
      handler4 = debounce(handler4, wait);
    }
    if (modifiers.includes("throttle")) {
      let nextModifier = modifiers[modifiers.indexOf("throttle") + 1] || "invalid-wait";
      let wait = isNumeric(nextModifier.split("ms")[0]) ? Number(nextModifier.split("ms")[0]) : 250;
      handler4 = throttle(handler4, wait);
    }
    if (modifiers.includes("prevent"))
      handler4 = wrapHandler(handler4, (next, e) => {
        e.preventDefault();
        next(e);
      });
    if (modifiers.includes("stop"))
      handler4 = wrapHandler(handler4, (next, e) => {
        e.stopPropagation();
        next(e);
      });
    if (modifiers.includes("once")) {
      handler4 = wrapHandler(handler4, (next, e) => {
        next(e);
        listenerTarget.removeEventListener(event, handler4, options);
      });
    }
    if (modifiers.includes("away") || modifiers.includes("outside")) {
      listenerTarget = document;
      handler4 = wrapHandler(handler4, (next, e) => {
        if (el.contains(e.target))
          return;
        if (e.target.isConnected === false)
          return;
        if (el.offsetWidth < 1 && el.offsetHeight < 1)
          return;
        if (el._x_isShown === false)
          return;
        next(e);
      });
    }
    if (modifiers.includes("self"))
      handler4 = wrapHandler(handler4, (next, e) => {
        e.target === el && next(e);
      });
    if (isKeyEvent(event) || isClickEvent(event)) {
      handler4 = wrapHandler(handler4, (next, e) => {
        if (isListeningForASpecificKeyThatHasntBeenPressed(e, modifiers)) {
          return;
        }
        next(e);
      });
    }
    listenerTarget.addEventListener(event, handler4, options);
    return () => {
      listenerTarget.removeEventListener(event, handler4, options);
    };
  }
  function dotSyntax(subject) {
    return subject.replace(/-/g, ".");
  }
  function camelCase2(subject) {
    return subject.toLowerCase().replace(/-(\w)/g, (match, char) => char.toUpperCase());
  }
  function isNumeric(subject) {
    return !Array.isArray(subject) && !isNaN(subject);
  }
  function kebabCase2(subject) {
    if ([" ", "_"].includes(
      subject
    ))
      return subject;
    return subject.replace(/([a-z])([A-Z])/g, "$1-$2").replace(/[_\s]/, "-").toLowerCase();
  }
  function isKeyEvent(event) {
    return ["keydown", "keyup"].includes(event);
  }
  function isClickEvent(event) {
    return ["contextmenu", "click", "mouse"].some((i) => event.includes(i));
  }
  function isListeningForASpecificKeyThatHasntBeenPressed(e, modifiers) {
    let keyModifiers = modifiers.filter((i) => {
      return !["window", "document", "prevent", "stop", "once", "capture", "self", "away", "outside", "passive"].includes(i);
    });
    if (keyModifiers.includes("debounce")) {
      let debounceIndex = keyModifiers.indexOf("debounce");
      keyModifiers.splice(debounceIndex, isNumeric((keyModifiers[debounceIndex + 1] || "invalid-wait").split("ms")[0]) ? 2 : 1);
    }
    if (keyModifiers.includes("throttle")) {
      let debounceIndex = keyModifiers.indexOf("throttle");
      keyModifiers.splice(debounceIndex, isNumeric((keyModifiers[debounceIndex + 1] || "invalid-wait").split("ms")[0]) ? 2 : 1);
    }
    if (keyModifiers.length === 0)
      return false;
    if (keyModifiers.length === 1 && keyToModifiers(e.key).includes(keyModifiers[0]))
      return false;
    const systemKeyModifiers = ["ctrl", "shift", "alt", "meta", "cmd", "super"];
    const selectedSystemKeyModifiers = systemKeyModifiers.filter((modifier) => keyModifiers.includes(modifier));
    keyModifiers = keyModifiers.filter((i) => !selectedSystemKeyModifiers.includes(i));
    if (selectedSystemKeyModifiers.length > 0) {
      const activelyPressedKeyModifiers = selectedSystemKeyModifiers.filter((modifier) => {
        if (modifier === "cmd" || modifier === "super")
          modifier = "meta";
        return e[`${modifier}Key`];
      });
      if (activelyPressedKeyModifiers.length === selectedSystemKeyModifiers.length) {
        if (isClickEvent(e.type))
          return false;
        if (keyToModifiers(e.key).includes(keyModifiers[0]))
          return false;
      }
    }
    return true;
  }
  function keyToModifiers(key) {
    if (!key)
      return [];
    key = kebabCase2(key);
    let modifierToKeyMap = {
      "ctrl": "control",
      "slash": "/",
      "space": " ",
      "spacebar": " ",
      "cmd": "meta",
      "esc": "escape",
      "up": "arrow-up",
      "down": "arrow-down",
      "left": "arrow-left",
      "right": "arrow-right",
      "period": ".",
      "comma": ",",
      "equal": "=",
      "minus": "-",
      "underscore": "_"
    };
    modifierToKeyMap[key] = key;
    return Object.keys(modifierToKeyMap).map((modifier) => {
      if (modifierToKeyMap[modifier] === key)
        return modifier;
    }).filter((modifier) => modifier);
  }


  directive("model", (el, { modifiers, expression }, { effect: effect3, cleanup: cleanup2 }) => {
    let scopeTarget = el;
    if (modifiers.includes("parent")) {
      scopeTarget = el.parentNode;
    }
    let evaluateGet = evaluateLater(scopeTarget, expression);
    let evaluateSet;
    if (typeof expression === "string") {
      evaluateSet = evaluateLater(scopeTarget, `${expression} = __placeholder`);
    } else if (typeof expression === "function" && typeof expression() === "string") {
      evaluateSet = evaluateLater(scopeTarget, `${expression()} = __placeholder`);
    } else {
      evaluateSet = () => {
      };
    }
    let getValue = () => {
      let result;
      evaluateGet((value) => result = value);
      return isGetterSetter(result) ? result.get() : result;
    };
    let setValue = (value) => {
      let result;
      evaluateGet((value2) => result = value2);
      if (isGetterSetter(result)) {
        result.set(value);
      } else {
        evaluateSet(() => {
        }, {
          scope: { "__placeholder": value }
        });
      }
    };
    if (typeof expression === "string" && el.type === "radio") {
      mutateDom(() => {
        if (!el.hasAttribute("name"))
          el.setAttribute("name", expression);
      });
    }
    var event = el.tagName.toLowerCase() === "select" || ["checkbox", "radio"].includes(el.type) || modifiers.includes("lazy") ? "change" : "input";
    let removeListener = isCloning ? () => {
    } : on(el, event, modifiers, (e) => {
      setValue(getInputValue(el, modifiers, e, getValue()));
    });
    if (modifiers.includes("fill")) {
      if ([void 0, null, ""].includes(getValue()) || isCheckbox(el) && Array.isArray(getValue()) || el.tagName.toLowerCase() === "select" && el.multiple) {
        setValue(
          getInputValue(el, modifiers, { target: el }, getValue())
        );
      }
    }
    if (!el._x_removeModelListeners)
      el._x_removeModelListeners = {};
    el._x_removeModelListeners["default"] = removeListener;
    cleanup2(() => el._x_removeModelListeners["default"]());
    if (el.form) {
      let removeResetListener = on(el.form, "reset", [], (e) => {
        nextTick(() => el._x_model && el._x_model.set(getInputValue(el, modifiers, { target: el }, getValue())));
      });
      cleanup2(() => removeResetListener());
    }
    el._x_model = {
      get() {
        return getValue();
      },
      set(value) {
        setValue(value);
      }
    };
    el._x_forceModelUpdate = (value) => {
      if (value === void 0 && typeof expression === "string" && expression.match(/\./))
        value = "";
      window.fromModel = true;
      mutateDom(() => bind(el, "value", value));
      delete window.fromModel;
    };
    effect3(() => {
      let value = getValue();
      if (modifiers.includes("unintrusive") && document.activeElement.isSameNode(el))
        return;
      el._x_forceModelUpdate(value);
    });
  });
  function getInputValue(el, modifiers, event, currentValue) {
    return mutateDom(() => {
      if (event instanceof CustomEvent && event.detail !== void 0)
        return event.detail !== null && event.detail !== void 0 ? event.detail : event.target.value;
      else if (isCheckbox(el)) {
        if (Array.isArray(currentValue)) {
          let newValue = null;
          if (modifiers.includes("number")) {
            newValue = safeParseNumber(event.target.value);
          } else if (modifiers.includes("boolean")) {
            newValue = safeParseBoolean(event.target.value);
          } else {
            newValue = event.target.value;
          }
          return event.target.checked ? currentValue.includes(newValue) ? currentValue : currentValue.concat([newValue]) : currentValue.filter((el2) => !checkedAttrLooseCompare2(el2, newValue));
        } else {
          return event.target.checked;
        }
      } else if (el.tagName.toLowerCase() === "select" && el.multiple) {
        if (modifiers.includes("number")) {
          return Array.from(event.target.selectedOptions).map((option) => {
            let rawValue = option.value || option.text;
            return safeParseNumber(rawValue);
          });
        } else if (modifiers.includes("boolean")) {
          return Array.from(event.target.selectedOptions).map((option) => {
            let rawValue = option.value || option.text;
            return safeParseBoolean(rawValue);
          });
        }
        return Array.from(event.target.selectedOptions).map((option) => {
          return option.value || option.text;
        });
      } else {
        let newValue;
        if (isRadio(el)) {
          if (event.target.checked) {
            newValue = event.target.value;
          } else {
            newValue = currentValue;
          }
        } else {
          newValue = event.target.value;
        }
        if (modifiers.includes("number")) {
          return safeParseNumber(newValue);
        } else if (modifiers.includes("boolean")) {
          return safeParseBoolean(newValue);
        } else if (modifiers.includes("trim")) {
          return newValue.trim();
        } else {
          return newValue;
        }
      }
    });
  }
  function safeParseNumber(rawValue) {
    let number = rawValue ? parseFloat(rawValue) : null;
    return isNumeric2(number) ? number : rawValue;
  }
  function checkedAttrLooseCompare2(valueA, valueB) {
    return valueA == valueB;
  }
  function isNumeric2(subject) {
    return !Array.isArray(subject) && !isNaN(subject);
  }
  function isGetterSetter(value) {
    return value !== null && typeof value === "object" && typeof value.get === "function" && typeof value.set === "function";
  }


  directive("cloak", (el) => queueMicrotask(() => mutateDom(() => el.removeAttribute(prefix("cloak")))));


  addInitSelector(() => `[${prefix("init")}]`);
  directive("init", skipDuringClone((el, { expression }, { evaluate: evaluate2 }) => {
    if (typeof expression === "string") {
      return !!expression.trim() && evaluate2(expression, {}, false);
    }
    return evaluate2(expression, {}, false);
  }));


  directive("text", (el, { expression }, { effect: effect3, evaluateLater: evaluateLater2 }) => {
    let evaluate2 = evaluateLater2(expression);
    effect3(() => {
      evaluate2((value) => {
        mutateDom(() => {
          el.textContent = value;
        });
      });
    });
  });


  directive("html", (el, { expression }, { effect: effect3, evaluateLater: evaluateLater2 }) => {
    let evaluate2 = evaluateLater2(expression);
    effect3(() => {
      evaluate2((value) => {
        mutateDom(() => {
          el.innerHTML = value;
          el._x_ignoreSelf = true;
          initTree(el);
          delete el._x_ignoreSelf;
        });
      });
    });
  });


  mapAttributes(startingWith(":", into(prefix("bind:"))));
  var handler2 = (el, { value, modifiers, expression, original }, { effect: effect3, cleanup: cleanup2 }) => {
    if (!value) {
      let bindingProviders = {};
      injectBindingProviders(bindingProviders);
      let getBindings = evaluateLater(el, expression);
      getBindings((bindings) => {
        applyBindingsObject(el, bindings, original);
      }, { scope: bindingProviders });
      return;
    }
    if (value === "key")
      return storeKeyForXFor(el, expression);
    if (el._x_inlineBindings && el._x_inlineBindings[value] && el._x_inlineBindings[value].extract) {
      return;
    }
    let evaluate2 = evaluateLater(el, expression);
    effect3(() => evaluate2((result) => {
      if (result === void 0 && typeof expression === "string" && expression.match(/\./)) {
        result = "";
      }
      mutateDom(() => bind(el, value, result, modifiers));
    }));
    cleanup2(() => {
      el._x_undoAddedClasses && el._x_undoAddedClasses();
      el._x_undoAddedStyles && el._x_undoAddedStyles();
    });
  };
  handler2.inline = (el, { value, modifiers, expression }) => {
    if (!value)
      return;
    if (!el._x_inlineBindings)
      el._x_inlineBindings = {};
    el._x_inlineBindings[value] = { expression, extract: false };
  };
  directive("bind", handler2);
  function storeKeyForXFor(el, expression) {
    el._x_keyExpression = expression;
  }


  addRootSelector(() => `[${prefix("data")}]`);
  directive("data", (el, { expression }, { cleanup: cleanup2 }) => {
    if (shouldSkipRegisteringDataDuringClone(el))
      return;
    expression = expression === "" ? "{}" : expression;
    let magicContext = {};
    injectMagics(magicContext, el);
    let dataProviderContext = {};
    injectDataProviders(dataProviderContext, magicContext);
    let data2 = evaluate(el, expression, { scope: dataProviderContext });
    if (data2 === void 0 || data2 === true)
      data2 = {};
    injectMagics(data2, el);
    let reactiveData = reactive(data2);
    initInterceptors(reactiveData);
    let undo = addScopeToNode(el, reactiveData);
    reactiveData["init"] && evaluate(el, reactiveData["init"]);
    cleanup2(() => {
      reactiveData["destroy"] && evaluate(el, reactiveData["destroy"]);
      undo();
    });
  });
  interceptClone((from, to) => {
    if (from._x_dataStack) {
      to._x_dataStack = from._x_dataStack;
      to.setAttribute("data-has-alpine-state", true);
    }
  });
  function shouldSkipRegisteringDataDuringClone(el) {
    if (!isCloning)
      return false;
    if (isCloningLegacy)
      return true;
    return el.hasAttribute("data-has-alpine-state");
  }


  directive("show", (el, { modifiers, expression }, { effect: effect3 }) => {
    let evaluate2 = evaluateLater(el, expression);
    if (!el._x_doHide)
      el._x_doHide = () => {
        mutateDom(() => {
          el.style.setProperty("display", "none", modifiers.includes("important") ? "important" : void 0);
        });
      };
    if (!el._x_doShow)
      el._x_doShow = () => {
        mutateDom(() => {
          if (el.style.length === 1 && el.style.display === "none") {
            el.removeAttribute("style");
          } else {
            el.style.removeProperty("display");
          }
        });
      };
    let hide = () => {
      el._x_doHide();
      el._x_isShown = false;
    };
    let show = () => {
      el._x_doShow();
      el._x_isShown = true;
    };
    let clickAwayCompatibleShow = () => setTimeout(show);
    let toggle = once(
      (value) => value ? show() : hide(),
      (value) => {
        if (typeof el._x_toggleAndCascadeWithTransitions === "function") {
          el._x_toggleAndCascadeWithTransitions(el, value, show, hide);
        } else {
          value ? clickAwayCompatibleShow() : hide();
        }
      }
    );
    let oldValue;
    let firstTime = true;
    effect3(() => evaluate2((value) => {
      if (!firstTime && value === oldValue)
        return;
      if (modifiers.includes("immediate"))
        value ? clickAwayCompatibleShow() : hide();
      toggle(value);
      oldValue = value;
      firstTime = false;
    }));
  });


  directive("for", (el, { expression }, { effect: effect3, cleanup: cleanup2 }) => {
    let iteratorNames = parseForExpression(expression);
    let evaluateItems = evaluateLater(el, iteratorNames.items);
    let evaluateKey = evaluateLater(
      el,

      el._x_keyExpression || "index"
    );
    el._x_prevKeys = [];
    el._x_lookup = {};
    effect3(() => loop(el, iteratorNames, evaluateItems, evaluateKey));
    cleanup2(() => {
      Object.values(el._x_lookup).forEach((el2) => mutateDom(
        () => {
          destroyTree(el2);
          el2.remove();
        }
      ));
      delete el._x_prevKeys;
      delete el._x_lookup;
    });
  });
  function loop(el, iteratorNames, evaluateItems, evaluateKey) {
    let isObject2 = (i) => typeof i === "object" && !Array.isArray(i);
    let templateEl = el;
    evaluateItems((items) => {
      if (isNumeric3(items) && items >= 0) {
        items = Array.from(Array(items).keys(), (i) => i + 1);
      }
      if (items === void 0)
        items = [];
      let lookup = el._x_lookup;
      let prevKeys = el._x_prevKeys;
      let scopes = [];
      let keys = [];
      if (isObject2(items)) {
        items = Object.entries(items).map(([key, value]) => {
          let scope2 = getIterationScopeVariables(iteratorNames, value, key, items);
          evaluateKey((value2) => {
            if (keys.includes(value2))
              warn("Duplicate key on x-for", el);
            keys.push(value2);
          }, { scope: { index: key, ...scope2 } });
          scopes.push(scope2);
        });
      } else {
        for (let i = 0; i < items.length; i++) {
          let scope2 = getIterationScopeVariables(iteratorNames, items[i], i, items);
          evaluateKey((value) => {
            if (keys.includes(value))
              warn("Duplicate key on x-for", el);
            keys.push(value);
          }, { scope: { index: i, ...scope2 } });
          scopes.push(scope2);
        }
      }
      let adds = [];
      let moves = [];
      let removes = [];
      let sames = [];
      for (let i = 0; i < prevKeys.length; i++) {
        let key = prevKeys[i];
        if (keys.indexOf(key) === -1)
          removes.push(key);
      }
      prevKeys = prevKeys.filter((key) => !removes.includes(key));
      let lastKey = "template";
      for (let i = 0; i < keys.length; i++) {
        let key = keys[i];
        let prevIndex = prevKeys.indexOf(key);
        if (prevIndex === -1) {
          prevKeys.splice(i, 0, key);
          adds.push([lastKey, i]);
        } else if (prevIndex !== i) {
          let keyInSpot = prevKeys.splice(i, 1)[0];
          let keyForSpot = prevKeys.splice(prevIndex - 1, 1)[0];
          prevKeys.splice(i, 0, keyForSpot);
          prevKeys.splice(prevIndex, 0, keyInSpot);
          moves.push([keyInSpot, keyForSpot]);
        } else {
          sames.push(key);
        }
        lastKey = key;
      }
      for (let i = 0; i < removes.length; i++) {
        let key = removes[i];
        if (!(key in lookup))
          continue;
        mutateDom(() => {
          destroyTree(lookup[key]);
          lookup[key].remove();
        });
        delete lookup[key];
      }
      for (let i = 0; i < moves.length; i++) {
        let [keyInSpot, keyForSpot] = moves[i];
        let elInSpot = lookup[keyInSpot];
        let elForSpot = lookup[keyForSpot];
        let marker = document.createElement("div");
        mutateDom(() => {
          if (!elForSpot)
            warn(`x-for ":key" is undefined or invalid`, templateEl, keyForSpot, lookup);
          elForSpot.after(marker);
          elInSpot.after(elForSpot);
          elForSpot._x_currentIfEl && elForSpot.after(elForSpot._x_currentIfEl);
          marker.before(elInSpot);
          elInSpot._x_currentIfEl && elInSpot.after(elInSpot._x_currentIfEl);
          marker.remove();
        });
        elForSpot._x_refreshXForScope(scopes[keys.indexOf(keyForSpot)]);
      }
      for (let i = 0; i < adds.length; i++) {
        let [lastKey2, index] = adds[i];
        let lastEl = lastKey2 === "template" ? templateEl : lookup[lastKey2];
        if (lastEl._x_currentIfEl)
          lastEl = lastEl._x_currentIfEl;
        let scope2 = scopes[index];
        let key = keys[index];
        let clone2 = document.importNode(templateEl.content, true).firstElementChild;
        let reactiveScope = reactive(scope2);
        addScopeToNode(clone2, reactiveScope, templateEl);
        clone2._x_refreshXForScope = (newScope) => {
          Object.entries(newScope).forEach(([key2, value]) => {
            reactiveScope[key2] = value;
          });
        };
        mutateDom(() => {
          lastEl.after(clone2);
          skipDuringClone(() => initTree(clone2))();
        });
        if (typeof key === "object") {
          warn("x-for key cannot be an object, it must be a string or an integer", templateEl);
        }
        lookup[key] = clone2;
      }
      for (let i = 0; i < sames.length; i++) {
        lookup[sames[i]]._x_refreshXForScope(scopes[keys.indexOf(sames[i])]);
      }
      templateEl._x_prevKeys = keys;
    });
  }
  function parseForExpression(expression) {
    let forIteratorRE = /,([^,\}\]]*)(?:,([^,\}\]]*))?$/;
    let stripParensRE = /^\s*\(|\)\s*$/g;
    let forAliasRE = /([\s\S]*?)\s+(?:in|of)\s+([\s\S]*)/;
    let inMatch = expression.match(forAliasRE);
    if (!inMatch)
      return;
    let res = {};
    res.items = inMatch[2].trim();
    let item = inMatch[1].replace(stripParensRE, "").trim();
    let iteratorMatch = item.match(forIteratorRE);
    if (iteratorMatch) {
      res.item = item.replace(forIteratorRE, "").trim();
      res.index = iteratorMatch[1].trim();
      if (iteratorMatch[2]) {
        res.collection = iteratorMatch[2].trim();
      }
    } else {
      res.item = item;
    }
    return res;
  }
  function getIterationScopeVariables(iteratorNames, item, index, items) {
    let scopeVariables = {};
    if (/^\[.*\]$/.test(iteratorNames.item) && Array.isArray(item)) {
      let names = iteratorNames.item.replace("[", "").replace("]", "").split(",").map((i) => i.trim());
      names.forEach((name, i) => {
        scopeVariables[name] = item[i];
      });
    } else if (/^\{.*\}$/.test(iteratorNames.item) && !Array.isArray(item) && typeof item === "object") {
      let names = iteratorNames.item.replace("{", "").replace("}", "").split(",").map((i) => i.trim());
      names.forEach((name) => {
        scopeVariables[name] = item[name];
      });
    } else {
      scopeVariables[iteratorNames.item] = item;
    }
    if (iteratorNames.index)
      scopeVariables[iteratorNames.index] = index;
    if (iteratorNames.collection)
      scopeVariables[iteratorNames.collection] = items;
    return scopeVariables;
  }
  function isNumeric3(subject) {
    return !Array.isArray(subject) && !isNaN(subject);
  }


  function handler3() {
  }
  handler3.inline = (el, { expression }, { cleanup: cleanup2 }) => {
    let root = closestRoot(el);
    if (!root._x_refs)
      root._x_refs = {};
    root._x_refs[expression] = el;
    cleanup2(() => delete root._x_refs[expression]);
  };
  directive("ref", handler3);


  directive("if", (el, { expression }, { effect: effect3, cleanup: cleanup2 }) => {
    if (el.tagName.toLowerCase() !== "template")
      warn("x-if can only be used on a <template> tag", el);
    let evaluate2 = evaluateLater(el, expression);
    let show = () => {
      if (el._x_currentIfEl)
        return el._x_currentIfEl;
      let clone2 = el.content.cloneNode(true).firstElementChild;
      addScopeToNode(clone2, {}, el);
      mutateDom(() => {
        el.after(clone2);
        skipDuringClone(() => initTree(clone2))();
      });
      el._x_currentIfEl = clone2;
      el._x_undoIf = () => {
        mutateDom(() => {
          destroyTree(clone2);
          clone2.remove();
        });
        delete el._x_currentIfEl;
      };
      return clone2;
    };
    let hide = () => {
      if (!el._x_undoIf)
        return;
      el._x_undoIf();
      delete el._x_undoIf;
    };
    effect3(() => evaluate2((value) => {
      value ? show() : hide();
    }));
    cleanup2(() => el._x_undoIf && el._x_undoIf());
  });


  directive("id", (el, { expression }, { evaluate: evaluate2 }) => {
    let names = evaluate2(expression);
    names.forEach((name) => setIdRoot(el, name));
  });
  interceptClone((from, to) => {
    if (from._x_ids) {
      to._x_ids = from._x_ids;
    }
  });


  mapAttributes(startingWith("@", into(prefix("on:"))));
  directive("on", skipDuringClone((el, { value, modifiers, expression }, { cleanup: cleanup2 }) => {
    let evaluate2 = expression ? evaluateLater(el, expression) : () => {
    };
    if (el.tagName.toLowerCase() === "template") {
      if (!el._x_forwardEvents)
        el._x_forwardEvents = [];
      if (!el._x_forwardEvents.includes(value))
        el._x_forwardEvents.push(value);
    }
    let removeListener = on(el, value, modifiers, (e) => {
      evaluate2(() => {
      }, { scope: { "$event": e }, params: [e] });
    });
    cleanup2(() => removeListener());
  }));


  warnMissingPluginDirective("Collapse", "collapse", "collapse");
  warnMissingPluginDirective("Intersect", "intersect", "intersect");
  warnMissingPluginDirective("Focus", "trap", "focus");
  warnMissingPluginDirective("Mask", "mask", "mask");
  function warnMissingPluginDirective(name, directiveName, slug) {
    directive(directiveName, (el) => warn(`You can't use [x-${directiveName}] without first installing the "${name}" plugin here: https://alpinejs.dev/plugins/${slug}`, el));
  }


  alpine_default.setEvaluator(normalEvaluator);
  alpine_default.setReactivityEngine({ reactive: reactive2, effect: effect2, release: stop, raw: toRaw });
  var src_default = alpine_default;


  window.Alpine = src_default;
  queueMicrotask(() => {
    src_default.start();
  });
})();
;
