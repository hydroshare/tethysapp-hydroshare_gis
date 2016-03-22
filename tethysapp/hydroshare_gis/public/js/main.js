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
 *                  http://bgrins.github.io/spectrum/
 *
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/

// Global directives for JSLint/JSHint
/*global
 document, $, console, FormData, ol, window, setTimeout, reproject, proj4,
 pageX, pageY, clearInterval, SLD_TEMPLATES, alert */

var HS_GIS = (function packageHydroShareGIS() {

    "use strict"; // And enable strict mode for this library

    /******************************************************
     ****************GLOBAL VARIABLES**********************
     ******************************************************/
    var contextMenuDict,
        dataTableLoadRes,
        layers,
        layersContextMenuGeneral,
        layersContextMenuShpfile,
        layersContextMenuTimeSeries,
        layerCount,
        map,
        fileLoaded,
        projectInfo,
    //  *********FUNCTIONS***********
        addLayerToUI,
        addDefaultBehaviorToAjax,
        addLoadResSelEvnt,
        addInitialEventListeners,
        areValidFiles,
        changeBaseMap,
        checkCsrfSafe,
        checkURLForParameters,
        closeLyrEdtInpt,
        displaySymbologyModalError,
        drawLayersInListOrder,
        editLayerName,
        generateAttributeTable,
        generateResourceList,
        getCookie,
        getCssStyles,
        getFilesSize,
        getGeomType,
        getRandomColor,
        hideMainLoadAnim,
        hideProgressBar,
        initializeJqueryVariables,
        initializeLayersContextMenu,
        initializeMap,
        loadResource,
        modifyDataTableDisplay,
        onClickDeleteLayer,
        onClickModifySymbology,
        onClickRenameLayer,
        onClickSaveProject,
        onClickShowAttrTable,
        onClickZoomToLayer,
        prepareFilesForAjax,
        processSaveProjectResponse,
        redrawDataTable,
        reprojectExtents,
        showMainLoadAnim,
        updateProgressBar,
        updateSymbology,
        updateUploadProgress,
        uploadFileButtonHandler,
        uploadResourceButtonHandler,
        zoomToLayer,
    //  **********Query Selectors************
        $btnApplySymbology,
        $btnSaveProject,
        $currentLayersList,
        $emptyBar,
        $loadingAnimMain,
        $modalAttrTbl,
        $modalInfo,
        $modalLoadFile,
        $modalLoadRes,
        $modalSymbology,
        $progressBar,
        $progressText,
        $uploadBtn;

    /******************************************************
     **************FUNCTION DECLARATIONS*******************
     ******************************************************/

    addLayerToUI = function (response) {
        var geoserverUrl,
            geomType,
            layerAttributes,
            layerExtents,
            layerName,
            layerId,
            layerIndex,
            newLayer,
            resType,
            rawLayerExtents,
            tsSiteInfo,
            $layerNameInput,
            $newLayerListElement;

        if (response.hasOwnProperty('success')) {
            geomType = getGeomType(response.geom_type);
            layerAttributes = response.layer_attributes;
            layerName = response.layer_name;
            layerId = response.layer_id || response.res_id;
            resType = response.res_type;
            rawLayerExtents = response.layer_extents;
            geoserverUrl = response.geoserver_url;
            tsSiteInfo = response.site_info;

            if (response.res_type === 'TimeSeriesResource') {
                layerExtents = ol.proj.fromLonLat([tsSiteInfo.lon, tsSiteInfo.lat]);
                newLayer = new ol.layer.Vector({
                    source: new ol.source.Vector({
                        features: [new ol.Feature(new ol.geom.Point(layerExtents))]
                    }),
                    style: new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 6,
                            fill: new ol.style.Fill({
                                color: getRandomColor()
                            })
                        })
                    })
                });
            } else {
                layerExtents = reprojectExtents(rawLayerExtents);
                newLayer = new ol.layer.Tile({
                    extent: layerExtents,
                    source: new ol.source.TileWMS({
                        url: geoserverUrl + '/wms',
                        params: {
                            'LAYERS': layerId,
                            'TILED': true
                        },
                        serverType: 'geoserver'
                    })
                });
            }

            map.addLayer(newLayer);

            layerIndex = layerCount.get();

            $currentLayersList.prepend(
                '<li class="ui-state-default" ' +
                'data-layer-index="' + layerIndex + '" ' +
                'data-layer-id="' + layerId + '" ' +
                'data-res-type="' + resType + '" ' +
                'data-geom-type="' + geomType + '" ' +
                'data-layer-attributes="' + layerAttributes + '">' +
                '<input class="chkbx-layer" type="checkbox" checked>' +
                '<span class="layer-name">' + layerName + '</span>' +
                '<input type="text" class="edit-layer-name hidden" value="' + layerName + '">' +
                '<div class="hmbrgr-div"><img src="/static/hydroshare_gis/images/hamburger-menu.svg"</div>' +
                '</li>'
            );

            projectInfo.map.layers[layerIndex] = {
                attributes: layerAttributes,
                geomType: geomType,
                id: layerId,
                index: layerIndex,
                listOrder: 1,
                name: layerName,
                resType: resType,
                sld: "Default",
                visible: true
            };

            drawLayersInListOrder();
            zoomToLayer(layerExtents, map.getSize(), resType);

            $newLayerListElement = $currentLayersList.find(':first-child');
            // Apply the dropdown-on-right-click menu to new layer in list

            $newLayerListElement.find('.hmbrgr-div img')
                .contextMenu('menu', contextMenuDict[resType], {
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
                var $layerNameSpan = $(this);

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
            $('#btn-upload-res').prop('disabled', false);
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

        $btnSaveProject.on('click', onClickSaveProject);

        $('.basemap-option').on('click', changeBaseMap);

        $modalLoadFile.on('hidden.bs.modal', function () {
            $('#input-files').val('');
            hideProgressBar();
        });

        $('#btn-upload-res').on('click', uploadResourceButtonHandler);

        $('#btn-upload-file').on('click', uploadFileButtonHandler);

        $('#input-files').on('change', function () {
            var files = this.files;
            if (!areValidFiles(files)) {
                $uploadBtn.attr('disabled', 'disabled');
                $('#msg-file')
                    .text("Invalid files. Include only one of the following 3 upload options below.")
                    .removeClass('hidden');
                setTimeout(function () {
                    $('#msg-file').addClass('hidden');
                }, 7000);
            } else {
                $uploadBtn.prop('disabled', false);
            }
        });

        map.getLayers().on('add', function () {
            layerCount.increase();
        });
        map.getLayers().on('remove', function () {
            layerCount.decrease();
        });

        $(document).on('change', '.chkbx-layer', function () {
            var index = Number($(this).parent().attr('data-layer-index'));
            map.getLayers().item(index).setVisible($(this).is(':checked'));
            projectInfo.map.layers[index].visible = $(this).is(':checked');
        });

        $modalLoadRes.on('shown.bs.modal', function () {
            if (dataTableLoadRes) {
                redrawDataTable(dataTableLoadRes, $(this));
            }
        });

        $('#chkbx-include-outline').on('change', function () {
            var outlineString,
                color;

            $('#outline-options').toggleClass('hidden');

            if ($('#outline-options').hasClass('hidden')) {
                $('#symbology-preview').css('outline', '0');
            } else {
                color = $('#poly-stroke').spectrum('get');
                if (color !== null) {
                    outlineString = $('#poly-stroke-width').val().toString();
                    outlineString += 'px solid ';
                    outlineString += color.toRgbString();
                    $('#symbology-preview').css('outline', outlineString);
                }
            }
        });

        $('#chkbx-include-labels').on('change', function () {
            $('#label-options').toggleClass('hidden');
            $('#label-preview').toggleClass('hidden');
        });

        $('#geom-fill').spectrum({
            showInput: true,
            allowEmpty: true,
            showAlpha: true,
            showPalette: true,
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                $('#symbology-preview').css('background-color', color.toRgbString());
                $btnApplySymbology.prop('disabled', false);
            }
        });

        $('#poly-stroke').spectrum({
            showInput: true,
            allowEmpty: true,
            showAlpha: true,
            showPalette: true,
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                var outlineString;
                outlineString = $('#poly-stroke-width').val().toString();
                outlineString += 'px solid ';
                outlineString += color.toRgbString();
                $('#symbology-preview').css('outline', outlineString);
                $btnApplySymbology.prop('disabled', false);
            }
        });

        $('#poly-stroke-width').on('change', function () {
            var outlineString;

            outlineString = $(this).val().toString();
            outlineString += 'px solid ';
            outlineString += $('#poly-stroke').spectrum('get').toRgbString();
            $('#symbology-preview').css('outline', outlineString);
        });

        $('#font-fill').spectrum({
            showInput: true,
            allowEmpty: true,
            showAlpha: true,
            showPalette: true,
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                if (color) {
                    $('#label-preview').css('color', color.toRgbString());
                    $btnApplySymbology.prop('disabled', false);
                } else {
                    $btnApplySymbology.prop('disabled', true);
                }
            }
        });

        $('#font-size').on('change', function () {
            $('#label-preview').css('font-size', $(this).val() + 'px');
        });

        $(window).on('resize', function () {
            $('#map').css('height', $('#app-content').height());
        });

        $btnApplySymbology.on('click', function () {
            updateSymbology($(this));
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

    displaySymbologyModalError = function (errorString) {
        $('#symbology-modal-info')
            .text(errorString)
            .removeClass('hidden');
        setTimeout(function () {
            $('#symbology-modal-info').addClass('hidden');
        }, 7000);
    };

    drawLayersInListOrder = function () {
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
            projectInfo.map.layers[index].listOrder = i - 2;
        }
    };

    editLayerName = function (e, $layerNameInput, $layerNameSpan, layerIndex) {
        var layerName;
        if (e.which === 13) {  // Enter key
            layerName = $layerNameInput.val();
            $layerNameSpan.text(layerName);
            projectInfo.map.layers[layerIndex].name = layerName;
            closeLyrEdtInpt($layerNameSpan, $layerNameInput);
        } else if (e.which === 27) {  // Esc key
            closeLyrEdtInpt($layerNameSpan, $layerNameInput);
        }
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
                    resTableHtml = '<table id="tbl-resources"><thead><th></th><th>Title</th><th>Size</th><th>Type</th><th>Owner</th></thead><tbody>';

                if (response.hasOwnProperty('success')) {
                    if (response.hasOwnProperty('resources')) {
                        resources = JSON.parse(response.resources);
                        resources.forEach(function (resource) {
                            resTableHtml += '<tr>' +
                                '<td><input type="radio" name="resource" class="rdo-res" value="' + resource.id + '"></td>' +
                                '<td class="res_title">' + resource.title + '</td>' +
                                '<td class="res_size">' + resource.size + '</td>' +
                                '<td class="res_type">' + resource.type + '</td>' +
                                '<td class="res_owner">' + resource.owner + '</td>' +
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
                        redrawDataTable(dataTableLoadRes, $modalLoadRes);

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

    getCssStyles = function (cssStyles, geomType) {
        var color;

        // Check conditions for the fill color
        if (geomType === 'point' || geomType === 'polygon') {
            color = $('#geom-fill').spectrum('get');
            if (color !== null) {
                cssStyles.fill = color.toHexString();
                cssStyles['fill-opacity'] = color.getAlpha().toString();
            } else {
                displaySymbologyModalError('You must select a fill color.');
                return;
            }
        }

        // Check conditions for the stroke (line) color
        if (geomType === 'line' || $('#chkbx-include-outline').is(':checked')) {
            color = $('#poly-stroke').spectrum('get');
            if (color !== null) {
                cssStyles.stroke = color.toHexString();
                cssStyles['stroke-opacity'] = color.getAlpha().toString();
                cssStyles['stroke-width'] = $('#poly-stroke-width').val();
            } else {
                displaySymbologyModalError('You must select a line color.');
            }
        } else {
            cssStyles.stroke = '#FFFFFF';
            cssStyles['stroke-opacity'] = "0";
            cssStyles['stroke-width'] = "0";
        }

        // Check conditions for the labels
        cssStyles.labels = $('#chkbx-include-labels').is(':checked');
        if (cssStyles.labels) {
            color = $('#font-fill').spectrum('get');
            if (color !== null) {
                cssStyles['label-field'] = $('#label-field').val();
                cssStyles['font-size'] = $('#font-size').val();
                cssStyles['font-fill'] = color.toHexString();
                cssStyles['font-fill-opacity'] = color.getAlpha().toString();
            } else {
                displaySymbologyModalError('You must select a font color.');
            }
        }

        if (geomType === 'point') {
            cssStyles['point-shape'] = $('#point-shape').val();
            cssStyles['point-size'] = $('#point-size').val();
        }

        return cssStyles;
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

    getGeomType = function (rawGeomType) {
        var geomType;

        if (rawGeomType.toLowerCase().indexOf('polygon') !== -1) {
            geomType = 'polygon';
        } else if (rawGeomType.toLowerCase().indexOf('point') !== -1) {
            geomType = 'point';
        } else if (rawGeomType.toLowerCase().indexOf('line') !== -1) {
            geomType = 'line';
        }
        return geomType;
    };

    getRandomColor = function () {
        var hexOptions = '0123456789ABCDEF',
            lettersList = hexOptions.split(''),
            color = '#',
            i;

        for (i = 0; i < 6; i++) {
            color += lettersList[Math.floor(Math.random() * 16)];
        }
        return color;
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
        $btnSaveProject = $('#btn-save');
        $btnApplySymbology = $('#btn-apply-symbology');
        $currentLayersList = $('#current-layers-list');
        $emptyBar = $('#empty-bar');
        $loadingAnimMain = $('#div-loading');
        $modalAttrTbl = $('#modalAttrTbl');
        $modalInfo = $('.modal-info');
        $modalLoadFile = $('#modalLoadFile');
        $modalLoadRes = $('#modalLoadRes');
        $modalSymbology = $('#modalSymbology');
        $progressBar = $('#progress-bar');
        $progressText = $('#progress-text');
        $uploadBtn = $('.btn-upload');
    };

    initializeLayersContextMenu = function () {
        layersContextMenuGeneral = [
            {
                name: 'Modify symbology',
                title: 'Modify symbology',
                fun: function (e) {
                    onClickModifySymbology(e);
                }
            }, {
                name: 'Rename',
                title: 'Rename',
                fun: function (e) {
                    onClickRenameLayer(e);
                }
            }, {
                name: 'Zoom to',
                title: 'Zoom to',
                fun: function (e) {
                    onClickZoomToLayer(e);
                }
            }, {
                name: 'Delete',
                title: 'Delete',
                fun: function (e) {
                    onClickDeleteLayer(e);
                }
            }
        ];

        layersContextMenuShpfile = layersContextMenuGeneral.slice();
        layersContextMenuShpfile.unshift({
            name: 'View attribute table',
            title: 'View attribute table',
            fun: function (e) {
                onClickShowAttrTable(e);
            }
        });

        layersContextMenuTimeSeries = layersContextMenuGeneral.slice();
        layersContextMenuTimeSeries.unshift({
            name: 'View time series',
            title: 'View time series'
            //fun: function (e) {
            //    var clickedElement = e.trigger.context,
            //        $dataElement = $(clickedElement).parent().parent(),
            //        resId = $dataElement.attr('data-layer-id');
            //
            //    console.log(resId);
            //}
        });

        contextMenuDict = {
            'GeographicFeatureResource': layersContextMenuShpfile,
            'TimeSeriesResource': layersContextMenuTimeSeries,
            'RefTimeSeriesResource': layersContextMenuTimeSeries,
            'RasterResource': layersContextMenuGeneral
        };
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
                $('#btn-upload-res').prop('disabled', false);
                console.error('Failure!');
            },
            success: function (response) {
                $modalInfo.addClass('hidden');
                $('#btn-upload-res').prop('disabled', false);
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

    onClickDeleteLayer = function (e) {
        var clickedElement = e.trigger.context,
            count,
            $dataElement = $(clickedElement).parent().parent(),
            deleteIndex = Number($dataElement.attr('data-layer-index')),
            i,
            index,
            layer;

        map.getLayers().removeAt(deleteIndex);
        $dataElement.remove();
        delete projectInfo.map.layers[deleteIndex];

        count = layerCount.get();
        for (i = 3; i <= count; i++) {
            layer = $currentLayersList.find('li:nth-child(' + (i - 2) + ')');
            index = Number(layer.attr('data-layer-index'));
            if (index > deleteIndex) {
                layer.attr('data-layer-index', index - 1);
            }
        }
    };

    onClickModifySymbology = function (e) {
        var clickedElement = e.trigger.context,
            $dataElement = $(clickedElement).parent().parent(),
            geomType = $dataElement.attr('data-geom-type'),
            layerId = $dataElement.attr('data-layer-id'),
            layerIndex = $dataElement.attr('data-layer-index'),
            labelFieldOptions = $dataElement.attr('data-layer-attributes').split(','),
            optionsHtmlString = '';

        $modalSymbology.find('.modal-title').text('Modify Symbology for: ' + $dataElement.find('.layer-name').text());
        $modalSymbology.find('#btn-apply-symbology').attr({
            'data-geom-type': geomType,
            'data-layer-id': layerId,
            'data-layer-index': layerIndex
        });

        labelFieldOptions.forEach(function (option) {
            optionsHtmlString += '<option value="' + option + '">' + option + '</option>';
        });
        $('#label-field').html(optionsHtmlString);

        $modalSymbology.find('fieldset').addClass('hidden');

        if (geomType === 'polygon') {
            $('.polygon').removeClass('hidden');
        } else if (geomType === 'point') {
            $('.point').removeClass('hidden');
        } else if (geomType === 'line') {
            $('#chkbx-include-outline').prop('checked', true);
            $('.line').removeClass('hidden');
        }
        $modalSymbology.modal('show');
    };

    onClickRenameLayer = function (e) {
        var clickedElement = e.trigger.context,
            $dataElement = $(clickedElement).parent().parent(),
            $LayerNameSpan = $dataElement.find('span'),
            layerIndex = $dataElement.attr('data-layer-index');

        $LayerNameSpan.addClass('hidden');
        $dataElement.find('input')
            .removeClass('hidden')
            .select()
            .on('keyup', function (e) {
                editLayerName(e, $(this), $LayerNameSpan, layerIndex);
            });
    };

    onClickSaveProject = function () {
        projectInfo.map.baseMap = $('.selected-basemap-option').attr('value');
        projectInfo.map.center = map.getView().getCenter();
        projectInfo.map.zoomLevel = map.getView().getZoom();

        $.ajax({
            type: 'GET',
            url: 'save-project',
            dataType: 'json',
            contentType: 'json',
            data: {
                'projectInfo': JSON.stringify(projectInfo)
            },
            error: function () {
                alert('An error occurred while attempting to save the project!');
            },
            success: function (response) {
                processSaveProjectResponse(response);
            }
        });
    };

    onClickShowAttrTable = function (e) {
        showMainLoadAnim();
        var clickedElement = e.trigger.context,
            $dataElement = $(clickedElement).parent().parent(),
            layerName = $dataElement.text(),
            layerId = $dataElement.attr('data-layer-id'),
            layerAttributes = $dataElement.attr('data-layer-attributes');

        generateAttributeTable(layerId, layerAttributes, layerName);
    };

    onClickZoomToLayer = function (e) {
        var clickedElement,
            index,
            layerExtent,
            resType,
            $dataElement;

        clickedElement = e.trigger.context;
        $dataElement = $(clickedElement).parent().parent();
        index = Number($dataElement.attr('data-layer-index'));
        resType = $dataElement.attr('data-res-type');
        if (resType === 'TimeSeriesResource') {
            layerExtent = map.getLayers().item(3).getSource().getFeatures()[0].getGeometry().getCoordinates();
        } else {
            layerExtent = map.getLayers().item(index).getExtent();
        }

        zoomToLayer(layerExtent, map.getSize(), resType);
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

    processSaveProjectResponse = function (response) {
        console.log(response);
    };

    redrawDataTable = function (dataTable, $modal) {
        var interval;
        interval = window.setInterval(function () {
            if ($modal.css('display') !== 'none' && $modal.find('table').length > 0) {
                $modal.find('.dataTables_scrollBody').css('height', $modal.find('.modal-body').height().toString() - 125 + 'px');
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

    updateSymbology = function ($this) {
        var geomType = $this.attr('data-geom-type'),
            layerId = $this.attr('data-layer-id'),
            layerIndex = $this.attr('data-layer-index'),
            sldString,
            cssStyles = {
                'layer-id': layerId
            };

        cssStyles = getCssStyles(cssStyles, geomType);
        if (cssStyles === null) {
            return;
        }
        sldString = SLD_TEMPLATES.getSldString(cssStyles, geomType);

        map.getLayers().item(layerIndex).getSource().updateParams({'SLD_BODY': sldString});
        projectInfo.map.layers[layerIndex].sld = sldString;
    };

    updateUploadProgress = function (fileSize, currProg) {
        var progress;

        currProg = currProg || 0;
        if (!fileLoaded) {
            currProg += 100000;
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
        var files = $('#input-files')[0].files,
            data,
            fileSize;

        $uploadBtn.prop('disabled', true);
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
                $('#btn-upload-file').prop('disabled', false);
                console.error("Error!");
            },
            success: function (response) {
                fileLoaded = true;
                updateProgressBar('100%');
                $('#btn-upload-file').prop('disabled', false);
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
    };

    uploadResourceButtonHandler = function () {

        $uploadBtn.attr('disabled', 'disabled');
        var $rdoRes = $('.rdo-res:checked'),
            resId = $rdoRes.val(),
            resType = $rdoRes.parent().parent().find('.res_type').text(),
            resTitle = $rdoRes.parent().parent().find('.res_title').text();

        loadResource(resId, resType, resTitle);
    };

    zoomToLayer = function (layerExtent, mapSize, resType) {
        if (resType === 'TimeSeriesResource') {
            map.getView().setCenter(layerExtent);
            map.getView().setZoom(16);
        } else {
            map.getView().fit(layerExtent, mapSize);
            if (map.getView().getZoom() > 16) {
                map.getView().setZoom(16);
            }
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
            stop: drawLayersInListOrder
        });
        $currentLayersList.disableSelection();
    });

    $('#modalWelcome').modal('show');

    /*-----------------------------------------------
     ***************INVOKE IMMEDIATELY***************
     ----------------------------------------------*/
    generateResourceList();

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

    projectInfo = {
        'map': {
            'baseMap': null,
            'layers': {},
            'zoomLevel': null,
            'center': null
        }
    };
}());
