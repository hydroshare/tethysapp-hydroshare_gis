/*****************************************************************************
 * FILE:    Main
 * DATE:    2/2/2016
 * AUTHOR:  Shawn Crawley
 * COPYRIGHT: (c) 2015 Brigham Young University
 * LICENSE: BSD 2-Clause
 * CONTRIBUTIONS:   http://ignitersworld.com/lab/contextMenu.html
 *                  http://openlayers.org/
 *                  https://www.npmjs.com/package/reproject
 *                  http://www.ajaxload.info/
 *                  http://datatables.net/
 *
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/

// Global directives for JSLint/JSHint
/*global document, $, console, FormData, ol, window, setTimeout, reproject, proj4, pageX, pageY, clearInterval */

var HS_GIS = (function packageHydroShareGIS() {

    "use strict"; // And enable strict mode for this library

    /******************************************************
     ****************GLOBAL VARIABLES**********************
     ******************************************************/
    var dataTableLoadRes,
        layers,
        layersContextMenuGeneral,
        layersContextMenuVector,
        layerCount,
        map,
        fileLoaded,
    // Functions
        addLayerToUI,
        addDefaultBehaviorToAjax,
        addLoadResSelEvnt,
        addInitialEventListeners,
        areValidFiles,
        changeBaseMap,
        checkCsrfSafe,
        checkURLForParameters,
        closeLyrEdtInpt,
        editLayerName,
        enableUploadBtn,
        generateAttributeTable,
        generateResourceList,
        getCookie,
        getFilesSize,
        hideMainLoadAnim,
        hideProgressBar,
        initializeJqueryVariables,
        initializeLayersContextMenu,
        initializeMap,
        loadResource,
        modifyDataTableDisplay,
        prepareFilesForAjax,
        redrawDataTable,
        reprojectExtents,
        showMainLoadAnim,
        updateProgressBar,
        updateUploadProgress,
        uploadFileButtonHandler,
        uploadResourceButtonHandler,
        zoomToLayer,
    //jQuery Selectors
        $currentLayersList,
        $emptyBar,
        $loadingAnimMain,
        $modalAttrTbl,
        $modalInfo,
        $modalLoadFile,
        $modalLoadRes,
        $progressBar,
        $progressText,
        $uploadBtn;

    /******************************************************
     **************FUNCTION DECLARATIONS*******************
     ******************************************************/

    addLayerToUI = function (response) {
        var contextMenu,
            geoserverUrl,
            layerAttributes,
            layerName,
            layerId,
            newLayer,
            resType,
            rawLayerExtents,
            $layerNameInput,
            $newLayerListElement;

        if (response.hasOwnProperty('success')) {
            layerAttributes = response.layer_attributes;
            layerName = response.layer_name;
            layerId = response.layer_id;
            resType = response.res_type;
            rawLayerExtents = response.layer_extents;
            geoserverUrl = response.geoserver_url;

            newLayer = new ol.layer.Tile({
                extent: reprojectExtents(rawLayerExtents),
                source: new ol.source.TileWMS({
                    url: geoserverUrl + '/wms',
                    params: {'LAYERS': layerId, 'TILED': true},
                    serverType: 'geoserver'
                })
            });
            map.addLayer(newLayer);
            zoomToLayer(newLayer.getExtent(), map.getSize());

            $currentLayersList.prepend(
                '<li class="ui-state-default" data-layer-index="' + layerCount.get() + '" data-layer-id="' + layerId + '" data-layer-attributes="' + layerAttributes + '">' +
                    '<input class="chkbx-layer" type="checkbox" checked>' +
                    '<span class="layer-name">' + layerName + '</span>' +
                    '<input type="text" class="edit-layer-name hidden" value="' + layerName + '">' +
                    '<div class="hmbrgr-div"><img src="/static/hydroshare_gis/images/hamburger-menu.svg"</div>' +
                    '</li>'
            );
            $newLayerListElement = $currentLayersList.find(':first-child');
            // Apply the dropdown-on-right-click menu to new layer in list
            contextMenu = (resType === 'GeographicFeatureResource') ? layersContextMenuVector : layersContextMenuGeneral;
            $newLayerListElement.find('.hmbrgr-div img')
                .contextMenu('menu', contextMenu, {
                    'triggerOn': 'click',
                    'displayAround': 'trigger',
                    'mouseClick': 'left',
                    'position': 'right',
                    'onOpen': function (e) {
                        $(e.trigger.context).parent().addClass('hmbrgr-open');
                    },
                    'onClose': function (e) {
                        $(e.trigger.context).parent().removeClass('hmbrgr-open');
                    }
                });

            $newLayerListElement.find('.layer-name').on('dblclick', function () {
                var $layerNameSpan = $(this),
                    layerIndex = Number($currentLayersList.find('li').index($newLayerListElement)) + 3;

                $layerNameSpan.addClass('hidden');
                $layerNameInput = $newLayerListElement.find('input[type=text]');
                $layerNameInput
                    .removeClass('hidden')
                    .select()
                    .on('keyup', function (e) {
                        editLayerName(e, $(this), $layerNameSpan, layerIndex);
                    })
                    .on('click', function (e) {
                        e.stopPropagation();
                    });

                $(document).on('click.edtLyrNm', function () {
                    closeLyrEdtInpt($layerNameSpan, $layerNameInput);
                });
            });
        }
    };

    addDefaultBehaviorToAjax = function () {
        // Add CSRF token to appropriate ajax requests
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!checkCsrfSafe(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
                }
            }
        });
    };

    addLoadResSelEvnt = function () {
        $modalLoadRes.find('tbody tr').on('click', function () {
            $(this)
                .css({
                    'background-color': '#1abc9c',
                    'color': 'white'
                })
                .find('input').prop('checked', true);
            $('tr').not($(this)).css({
                'background-color': '',
                'color': ''
            });
        });
    };

    addInitialEventListeners = function () {
        $('.basemap-option').on('click', changeBaseMap);

        $modalLoadFile.on('hidden.bs.modal', function () {
            $('#input-files').val('');
            hideProgressBar();
            enableUploadBtn();
        });

        $modalLoadRes.on('hidden.bs.modal', function () {
            enableUploadBtn();
        });

        $('#btn-upload-res').on('click', uploadResourceButtonHandler);

        $('#btn-upload-file').on('click', uploadFileButtonHandler);

        map.getLayers().on('add', function () {
            layerCount.increase();
        });
        map.getLayers().on('remove', function () {
            layerCount.decrease();
        });

        $(document).on('change', '.chkbx-layer', function () {
            var index = Number($(this).parent().attr('data-layer-index'));

            if ($(this).is(':checked')) {
                map.getLayers().item(index).setVisible(true);
            } else {
                map.getLayers().item(index).setVisible(false);
            }
        });

        $modalLoadRes.on('shown.bs.modal', function () {
            $('.dataTables_scrollBody').css('height', $(this).find('.modal-body').height().toString() - 125 + 'px');
            redrawDataTable(dataTableLoadRes, $(this));
        });
    };

    areValidFiles = function (files) {
        var file,
            fileCount = 0,
            hasShp = false,
            hasShx = false,
            hasPrj = false,
            hasDbf = false,
            hasTif = false,
            hasZip = false;

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                if (++fileCount > 4) {
                    return false;
                }
                if (files.hasOwnProperty(file)) {
                    if (files[file].name.endsWith('.shp')) {
                        hasShp = true;
                    } else if (files[file].name.endsWith('.shx')) {
                        hasShx = true;
                    } else if (files[file].name.endsWith('.prj')) {
                        hasPrj = true;
                    } else if (files[file].name.endsWith('.dbf')) {
                        hasDbf = true;
                    } else if (files[file].name.endsWith('.tif')) {
                        hasTif = true;
                    } else if (files[file].name.endsWith('.zip')) {
                        hasZip = true;
                    }
                }
            }
        }
        return (((hasTif || hasZip) && fileCount === 1) || (hasShp && hasShx && hasPrj && hasDbf));
    };

    changeBaseMap = function () {
        $('.current-basemap-label').text('');
        $('.basemap-option').removeClass('selected-basemap-option');
        $(this).addClass('selected-basemap-option');
        $($(this).children()[0]).text(' (Current)');

        var style = $(this).attr('value'),
            i,
            ii = layers.length;

        for (i = 0; i < ii; ++i) {
            layers[i].set('visible', (layers[i].get('style') === style));
        }
    };

// Find if method is CSRF safe
    checkCsrfSafe = function (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    checkURLForParameters = function () {
        var transformToAssocArray = function (prmstr) {
                var i,
                    params = {},
                    prmArr = prmstr.split("&"),
                    tmpArr;

                for (i = 0; i < prmArr.length; i++) {
                    tmpArr = prmArr[i].split("=");
                    params[tmpArr[0]] = tmpArr[1];
                }
                return params;
            },
            getSearchParameters = function () {
                var prmstr = window.location.search.substr(1);
                return prmstr !== null && prmstr !== "" ? transformToAssocArray(prmstr) : {};
            },
            params = getSearchParameters();

        if (params.res_id !== undefined || params.res_id !== null) {
            if (params.src === 'hs') {
                showMainLoadAnim();
                loadResource(params.res_id);
            }
        }
    };

    closeLyrEdtInpt = function ($layerNameSpan, $layerNameInput) {
        $layerNameInput
            .addClass('hidden')
            .off('keyup')
            .off('click');
        $layerNameSpan.removeClass('hidden');
        $(document).off('click.edtLyrNm');
    };

    editLayerName = function (e, $layerNameInput, $layerNameSpan) {
        if (e.which === 13) {  // Enter key
            $layerNameSpan.text($layerNameInput.val());
            closeLyrEdtInpt($layerNameSpan, $layerNameInput);
        } else if (e.which === 27) {  // Esc key
            closeLyrEdtInpt($layerNameSpan, $layerNameInput);
        }
    };

    enableUploadBtn = function () {
        $uploadBtn
            .text('Upload')
            .removeAttr('disabled');
    };

    generateAttributeTable = function (layerId, layerAttributes, layerName) {
        $.ajax({
            type: 'GET',
            url: 'generate-attribute-table',
            data: {
                'layerId': layerId,
                'layerAttributes': layerAttributes
            },
            error: function () {
                console.error('There was an error when performing the ajax request to \'generate_attribute_table\'');
            },
            success: function (response) {
                var attributeTableHTML,
                    currAttrVal,
                    featureProperties,
                    i,
                    j,
                    layerAttributesList = [],
                    length,
                    numAttributes,
                    dataTable,
                    tableHeadingHTML = '';

                if (response.hasOwnProperty('success')) {
                    featureProperties = JSON.parse(response.feature_properties);
                    layerAttributesList = layerAttributes.split(',');
                    numAttributes = layerAttributesList.length;
                    for (i = 0; i < numAttributes; i++) {
                        tableHeadingHTML += '<th>' + layerAttributesList[i] + '</th>';
                    }
                    attributeTableHTML = '<table id="tbl-attributes"><thead>' + tableHeadingHTML + '</thead><tbody>';

                    for (i = 0, length = featureProperties.length; i < length; i++) {
                        attributeTableHTML += '<tr>';
                        for (j = 0; j < numAttributes; j++) {
                            currAttrVal = featureProperties[i][layerAttributesList[j]];
                            attributeTableHTML += '<td class="attribute" data-attribute="' + layerAttributesList[j] + '">' + currAttrVal + '</td>';
                        }
                        attributeTableHTML += '</tr>';
                    }
                    $modalAttrTbl.find('.modal-body').html(attributeTableHTML);
                    dataTable = $('#tbl-attributes').DataTable({
                        'order': [[0, 'asc']],
                        "scrollY": "100%",
                        "scrollCollapse": true,
                        fixedHeader: {
                            header: true,
                            footer: true
                        }
                    });
                    hideMainLoadAnim();
                    $modalAttrTbl.find('.modal-title').text('Attributes for layer: ' + layerName);
                    modifyDataTableDisplay(dataTable, $modalAttrTbl);
                    $modalAttrTbl.modal('show');
                }
            }
        });
    };

    generateResourceList = function (numRequests) {
        $.ajax({
            type: 'GET',
            url: 'get-hs-res-list',
            dataType: 'json',
            error: function () {
                if (numRequests < 5) {
                    numRequests += 1;
                    setTimeout(generateResourceList, 3000, numRequests);
                }
            },
            success: function (response) {
                var resources,
                    resTableHtml = '<table id="tbl-resources"><thead><th></th><th>Title</th><th>Type</th></thead><tbody>';

                if (response.hasOwnProperty('success')) {
                    if (response.hasOwnProperty('resources')) {
                        resources = JSON.parse(response.resources);
                        resources.forEach(function (resource) {
                            resTableHtml += '<tr>' +
                                '<td><input type="radio" name="resource" class="rdo-res" value="' + resource.id + '"></td>' +
                                '<td class="res_title">' + resource.title + '</td>' +
                                '<td class="res_type">' + resource.type + '</td>' +
                                '</tr>';
                        });
                        resTableHtml += '</tbody></table>';
                        $modalLoadRes.find('.modal-body').html(resTableHtml);
                        addLoadResSelEvnt();
                        dataTableLoadRes = $('#tbl-resources').DataTable({
                            'order': [[1, 'asc']],
                            'columnDefs': [{
                                'orderable': false,
                                'targets': 0
                            }],
                            "scrollY": '500px',
                            "scrollCollapse": true,
                            fixedHeader: {
                                header: true,
                                footer: true
                            }
                        });

                        $('#btn-upload-res').add('#div-chkbx-res-auto-close').removeClass('hidden');
                    }
                }
            }
        });
    };

    getCookie = function (name) {
        var cookie,
            cookies,
            cookieValue = null,
            i;

        if (document.cookie && document.cookie !== '') {
            cookies = document.cookie.split(';');
            for (i = 0; i < cookies.length; i++) {
                cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    getFilesSize = function (files) {
        var file,
            fileSize = 0;

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                fileSize += files[file].size;
            }
        }
        return fileSize;
    };

    hideMainLoadAnim = function () {
        $('#app-content-wrapper').removeAttr('style');
        $loadingAnimMain.addClass('hidden');
    };

    hideProgressBar = function () {
        $progressBar.addClass('hidden');
        $progressText
            .addClass('hidden')
            .text('0%');
        $emptyBar.addClass('hidden');
    };

    initializeJqueryVariables = function () {
        $currentLayersList = $('#current-layers-list');
        $emptyBar = $('#empty-bar');
        $loadingAnimMain = $('#div-loading');
        $modalAttrTbl = $('#modalAttrTbl');
        $modalInfo = $('.modal-info');
        $modalLoadFile = $('#modalLoadFile');
        $modalLoadRes = $('#modalLoadRes');
        $progressBar = $('#progress-bar');
        $progressText = $('#progress-text');
        $uploadBtn = $('.btn-upload');
    };

    initializeLayersContextMenu = function () {
        layersContextMenuGeneral = [
            {
                name: 'Rename',
                title: 'Rename',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        $dataElement = $(clickedElement).parent().parent(),
                        index = Number($dataElement.attr('data-layer-index')),
                        $LayerNameSpan = $dataElement.find('span');
                    $LayerNameSpan.addClass('hidden');
                    $dataElement.find('input')
                        .removeClass('hidden')
                        .select()
                        .on('keyup', function (e) {
                            editLayerName(e, $(this), $LayerNameSpan, index);
                        });
                }
            }, {
                name: 'Zoom to',
                title: 'Zoom to',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        $dataElement = $(clickedElement).parent().parent(),
                        index = Number($dataElement.attr('data-layer-index')),
                        layerExtent = map.getLayers().item(index).getExtent();

                    zoomToLayer(layerExtent, map.getSize());
                }
            }, {
                name: 'Delete',
                title: 'Delete',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        count,
                        $dataElement = $(clickedElement).parent().parent(),
                        deleteIndex = Number($dataElement.attr('data-layer-index')),
                        i,
                        index,
                        layer;

                    map.getLayers().removeAt(deleteIndex);
                    $dataElement.remove();

                    count = layerCount.get();
                    for (i = 3; i <= count; i++) {
                        layer = $currentLayersList.find('li:nth-child(' + (i - 2) + ')');
                        index = Number(layer.attr('data-layer-index'));
                        if (index > deleteIndex) {
                            layer.attr('data-layer-index', index - 1);
                        }
                    }
                }
            }
        ];

        layersContextMenuVector = layersContextMenuGeneral.slice();
        layersContextMenuVector.unshift({
            name: 'View attribute table',
            title: 'View attribute table',
            fun: function (e) {
                showMainLoadAnim();
                var clickedElement = e.trigger.context,
                    $dataElement = $(clickedElement).parent().parent(),
                    layerName = $dataElement.text(),
                    layerId = $dataElement.attr('data-layer-id'),
                    layerAttributes = $dataElement.attr('data-layer-attributes');

                generateAttributeTable(layerId, layerAttributes, layerName);
            }
        });
    };

    initializeMap = function () {
        // Base Layer options
        layers = [
            new ol.layer.Tile({
                style: 'Road',
                visible: false,
                source: new ol.source.MapQuest({layer: 'osm'})
            }),
            new ol.layer.Tile({
                style: 'Aerial',
                visible: false,
                source: new ol.source.MapQuest({layer: 'sat'})
            }),
            new ol.layer.Group({
                style: 'AerialWithLabels',
                visible: false,
                layers: [
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'sat'})
                    }),
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'hyb'})
                    })
                ]
            })
        ];

        map = new ol.Map({
            layers: layers,
            target: 'map',
            view: new ol.View({
                center: [0, 0],
                zoom: 2
            })
        });
    };

    layerCount = (function () {
        // The count = 2 accounts for the 3 base maps added before this count is initialized
        var count = 2;
        return {
            'get': function () {
                return count;
            },
            'increase': function () {
                count += 1;
            },
            'decrease': function () {
                count -= 1;
            }
        };
    }());

    loadResource = function (res_id, res_type, res_title) {
        $modalInfo.removeClass('hidden');

        $.ajax({
            type: 'GET',
            url: 'load-file',
            dataType: 'json',
            data: {
                'res_id': res_id,
                'res_type': res_type,
                'res_title': res_title
            },
            error: function () {
                $modalInfo.addClass('hidden');
                enableUploadBtn();
                console.error('Failure!');
            },
            success: function (response) {
                $modalInfo.addClass('hidden');
                enableUploadBtn();
                hideMainLoadAnim();
                addLayerToUI(response);
                if ($('#chkbx-res-auto-close').is(':checked')) {
                    $modalLoadRes.modal('hide');
                }
            }
        });
    };

    modifyDataTableDisplay = function (dataTable, $modal) {
        $('.dataTables_scrollHead').css('overflow', 'auto');
        $('.dataTables_scrollHead').on('scroll', function (e) {
            $('.dataTables_scrollBody').scrollLeft($(e.currentTarget).scrollLeft());
        });
        $('.dataTables_scrollBody').on('scroll', function (e) {
            $('.dataTables_scrollHead').scrollLeft($(e.currentTarget).scrollLeft());
        });

        redrawDataTable(dataTable, $modal);
    };

    prepareFilesForAjax = function (files) {
        var file,
            data = new FormData();

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                data.append('files', files[file]);
            }
        }
        return data;
    };

    redrawDataTable = function (dataTable, $modal) {
        var interval;
        interval = window.setInterval(function () {
            if ($modal.css('display') !== 'none') {
                console.log('good to go');
                dataTable.columns.adjust().draw();
                window.clearInterval(interval);
            }
        }, 100);
    };

    reprojectExtents = function (rawExtents) {
        var crs,
            extentMaxX,
            extentMaxY,
            extentMinX,
            extentMinY,
            extents,
            tempCoord1,
            tempCoord2;

        if (typeof rawExtents === 'string') {
            rawExtents = JSON.parse(rawExtents);
        }
        extentMinX = Number(rawExtents.minx);
        extentMaxX = Number(rawExtents.maxx);
        extentMinY = Number(rawExtents.miny);
        extentMaxY = Number(rawExtents.maxy);

        crs = rawExtents.crs;
        proj4.defs('new_projection', crs);

        tempCoord1 = proj4(proj4('new_projection'), proj4('EPSG:3857'), [extentMinX, extentMinY]);
        tempCoord2 = proj4(proj4('new_projection'), proj4('EPSG:3857'), [extentMaxX, extentMaxY]);

        extents = tempCoord1.concat(tempCoord2);

        return extents;
    };

    showMainLoadAnim = function () {
        $('#app-content-wrapper').css({
            '-webkit-filter': 'blur(1px)',
            '-moz-filter': 'blur(1px)',
            '-o-filter': 'blur(1px)',
            '-ms-filter': 'blur(1px)',
            'filter': 'blur(1px)',
            'opacity': '0.5'
        });
        $loadingAnimMain.removeClass('hidden');

    };

    updateProgressBar = function (value) {
        $progressBar.css('width', value);
        $progressText.text(value);
    };

    updateUploadProgress = function (fileSize, currProg) {
        var progress;

        currProg = currProg === undefined ? 0 : currProg;
        if (!fileLoaded) {
            currProg += 1000000;
            progress = Math.round(currProg / fileSize * 100);
            progress = progress > 100 ? 100 : progress;
            updateProgressBar(parseInt(progress, 10) + '%');
            setTimeout(function () {
                updateUploadProgress(fileSize, currProg);
            }, 1000);
        } else {
            updateProgressBar('100%');
        }
    };

    uploadFileButtonHandler = function () {
        var fileInputNode = $('#input-files')[0],
            files = fileInputNode.files,
            data,
            fileSize;

        if (!areValidFiles(files)) {
            console.error("Invalid files. Include only one of the following three cases: 1) 4 files (.shp, .shx, .prj, and .dbf); 2) 1 file (.tif); 3) 1 file (.zip).");
        } else {
            $uploadBtn.text('...').attr('disabled', 'true');
            data = prepareFilesForAjax(files);
            fileSize = getFilesSize(files);
            fileLoaded = false;
            $.ajax({
                url: 'load-file/',
                type: 'POST',
                data: data,
                dataType: 'json',
                processData: false,
                contentType: false,
                error: function () {
                    $progressBar.addClass('hidden');
                    enableUploadBtn();
                    console.error("Error!");
                },
                success: function (response) {
                    fileLoaded = true;
                    updateProgressBar('100%');
                    enableUploadBtn();
                    addLayerToUI(response);
                    if ($('#chkbx-file-auto-close').is(':checked')) {
                        $modalLoadFile.modal('hide');
                    }
                }
            });

            $emptyBar.removeClass('hidden');
            $progressBar.removeClass('hidden');
            $progressText.removeClass('hidden');
            updateUploadProgress(fileSize);
        }
    };

    uploadResourceButtonHandler = function () {

        $uploadBtn.text('...').attr('disabled', 'true');
        var $rdoRes = $('.rdo-res:checked'),
            resId = $rdoRes.val(),
            resType = $rdoRes.parent().parent().find('.res_type').text(),
            resTitle = $rdoRes.parent().parent().find('.res_title').text();

        loadResource(resId, resType, resTitle);
    };

    zoomToLayer = function (layerExtent, mapSize) {
        map.getView().fit(layerExtent, mapSize);
        if (map.getView().getZoom() > 16) {
            map.getView().setZoom(16);
        }
    };

    /*-----------------------------------------------
     **************ONLOAD FUNCTION*******************
     ----------------------------------------------*/

    $(function () {
        $('#map').css('height', $('#app-content').height());
        initializeJqueryVariables();
        checkURLForParameters();
        addDefaultBehaviorToAjax();
        initializeMap();
        initializeLayersContextMenu();
        addInitialEventListeners();

        $currentLayersList.sortable({
            placeholder: "ui-state-highlight",
            stop: function () {
                var i,
                    index,
                    layer,
                    count,
                    zIndex;

                count = layerCount.get();
                for (i = 3; i <= count; i++) {
                    layer = $currentLayersList.find('li:nth-child(' + (i - 2) + ')');
                    index = Number(layer.attr('data-layer-index'));
                    zIndex = count - i;
                    map.getLayers().item(index).setZIndex(zIndex);
                }
            }
        });
        $currentLayersList.disableSelection();
    });

    $('#modalWelcome').modal('show');

    /*-----------------------------------------------
     ***************INVOKE IMMEDIATELY***************
     ----------------------------------------------*/
    generateResourceList();
}());
