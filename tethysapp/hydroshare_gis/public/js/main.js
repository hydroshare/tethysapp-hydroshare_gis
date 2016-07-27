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
// /*jslint
//  browser, this, devel, multivar
//  */
/*global
 document, $, console, FormData, ol, window, setTimeout, reproject, proj4,
 pageX, pageY, clearInterval, SLD_TEMPLATES, alert, tinycolor, jsPDF, MutationObserver
 */

(function packageHydroShareGIS() {

    "use strict"; // And enable strict mode for this library

    /******************************************************
     ****************GLOBAL VARIABLES**********************
     ******************************************************/
    var basemapLayers,
        contextMenuDict,
        dataTableLoadRes,
        insetMap,
        layersContextMenuBase,
        layersContextMenuGeospatialBase,
        layersContextMenuViewFile,
        layersContextMenuRaster,
        layersContextMenuVector,
        layersContextMenuTimeSeries,
        layerCount,
        map,
        projectInfo,
        //  *********FUNCTIONS***********
        addContextMenuToListItem,
        addGenericResToUI,
        addLayerToMap,
        addLayerToUI,
        addListenersToListItem,
        addDefaultBehaviorToAjax,
        addLoadResSelEvnt,
        addInitialEventListeners,
        areValidFiles,
        buildHSResTable,
        changeBaseMap,
        checkCsrfSafe,
        checkURLForParameters,
        closeLyrEdtInpt,
        createExportCanvas,
        createLayerListItem,
        displaySymbologyModalError,
        deletePublicTempfiles,
        drawLayersInListOrder,
        drawPointSymbologyPreview,
        editLayerDisplayName,
        generateAttributeTable,
        generateResourceList,
        getCookie,
        getCssStyles,
        getGeomType,
        getGeoserverUrl,
        getRandomColor,
        hideMainLoadAnim,
        initializeJqueryVariables,
        initializeLayersContextMenus,
        initializeMap,
        loadProjectFile,
        loadResource,
        modifyDataTableDisplay,
        onClickAddToExistingProject,
        onClickAddToNewProject,
        onClickDeleteLayer,
        onClickModifySymbology,
        onClickViewFile,
        onClickOpenInHS,
        onClickRenameLayer,
        onClickSaveNewProject,
        onClickShowAttrTable,
        onClickViewLegend,
        onClickZoomToLayer,
        prepareFilesForAjax,
        processAddHSResResults,
        processSaveNewProjectResponse,
        redrawDataTable,
        reprojectExtents,
        setupSymbologyLabelsState,
        setupSymbologyModalState,
        setupSymbologyPointState,
        setupSymbologyPolygonState,
        setupSymbologyPolylineState,
        setupSymbologyRasterState,
        setupSymbologyStrokeState,
        showMainLoadAnim,
        showResLoadingStatus,
        updateSymbology,
        uploadFileButtonHandler,
        uploadResourceButtonHandler,
        zoomToLayer,
        //  **********Query Selectors************
        $btnApplySymbology,
        $btnShowModalSaveNewProject,
        $btnSaveNewProject,
        $btnSaveProject,
        $currentLayersList,
        $loadingAnimMain,
        $modalAttrTbl,
        $modalLegend,
        $modalLoadFile,
        $modalLoadRes,
        $modalSaveNewProject,
        $modalSymbology,
        $modalViewFile,
        $uploadBtn;

    /******************************************************
     **************FUNCTION DECLARATIONS*******************
     ******************************************************/

    addContextMenuToListItem = function ($listItem, resType) {
        var contextMenuId;

        $listItem.find('.hmbrgr-div img')
            .contextMenu('menu', contextMenuDict[resType], {
                'triggerOn': 'click',
                'displayAround': 'trigger',
                'mouseClick': 'left',
                'position': 'right',
                'onOpen': function (e) {
                    $('.hmbrgr-div').removeClass('hmbrgr-open');
                    $(e.trigger.context).parent().addClass('hmbrgr-open');
                },
                'onClose': function (e) {
                    $(e.trigger.context).parent().removeClass('hmbrgr-open');
                }
            });
        contextMenuId = $('.iw-contextMenu:last-child').attr('id');
        $listItem.attr('data-context-menu', contextMenuId);
    };

    addGenericResToUI = function (results, isLastResource) {
        var $newLayerListItem;
        var iDisplayName = results.layer_name;
        var resId = results.res_id;
        var layerIndex = Math.floor(Math.random() * 1000) + 1000;
        var publicFilename = results.public_fname;
        var resType = results.res_type;

        createLayerListItem('prepend', layerIndex, 'None', resType, 'None', 'None', true, iDisplayName, 'None', resId, publicFilename, true);
        $newLayerListItem = $currentLayersList.find(':first-child');
        addListenersToListItem($newLayerListItem, layerIndex);
        addContextMenuToListItem($newLayerListItem, resType);

        // Add layer data to project info
        projectInfo.map.layers[iDisplayName] = {
            displayName: iDisplayName,
            hsResId: resId,
            resType: resType,
            filename: publicFilename,
            listOrder: 1
        };

        (function () {
            var numLayers = $currentLayersList.children().length;
            var i;
            var layer;
            for (i = 1; i <= numLayers; i++) {
                layer = $currentLayersList.find('li:nth-child(' + i + ')');
                iDisplayName = layer.find('.layer-name').text();
                projectInfo.map.layers[iDisplayName].listOrder = i;
            }
        }());

        if (isLastResource) {
            hideMainLoadAnim();
            showResLoadingStatus(true, 'Resource(s) added successfully!');
        }
    };

    addLayerToMap = function (data) {
        var lyrParams,
            newLayer = null,
            sldString,
            lyrExtents = data.lyrExtents,
            lyrId = data.lyrId,
            resType = data.resType,
            geomType = data.geomType,
            cssStyles = data.cssStyles,
            visible = data.visible,
            hide255 = data.hide255;

        if (resType.indexOf('TimeSeriesResource') > -1) {
            newLayer = new ol.layer.Vector({
                source: new ol.source.Vector({
                    features: [new ol.Feature(new ol.geom.Point(lyrExtents))]
                }),
                style: new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 6,
                        fill: new ol.style.Fill({
                            color: getRandomColor()
                        })
                    })
                }),
                visible: visible
            });
        } else {
            lyrParams = {
                'LAYERS': lyrId,
                'TILED': true
            };
            if (cssStyles && cssStyles !== 'Default') {
                sldString = SLD_TEMPLATES.getSldString(cssStyles, geomType, lyrId, hide255);
                lyrParams.SLD_BODY = sldString;
            }
            newLayer = new ol.layer.Tile({
                extent: lyrExtents,
                source: new ol.source.TileWMS({
                    url: projectInfo.map.geoserverUrl + '/wms',
                    params: lyrParams,
                    serverType: 'geoserver',
                    crossOrigin: 'Anonymous'
                }),
                visible: visible
            });
        }
        if (newLayer !== null) {
            map.addLayer(newLayer);
        }
    };

    addLayerToUI = function (results, isLastResource) {
        var geomType,
            hide255 = false,
            cssStyles,
            layerAttributes,
            layerExtents,
            displayName,
            layerId,
            layerIndex,
            resType,
            bandInfo,
            rawLayerExtents,
            resId,
            tsSiteInfo,
            $newLayerListItem;

        resId = results.res_id;
        resType = results.res_type;
        if (resType === 'GeographicFeatureResource') {
            geomType = getGeomType(results.geom_type);
            layerAttributes = results.layer_attributes;
        } else {
            geomType = "None";
            layerAttributes = "None";
        }
        bandInfo = (resType === 'RasterResource' && results.band_info) ? results.band_info : 'None';
        displayName = results.layer_name;
        layerId = results.layer_id || results.res_id;
        rawLayerExtents = results.layer_extents;

        if (resType.indexOf('TimeSeriesResource') > -1) {
            tsSiteInfo = results.site_info;
            layerExtents = ol.proj.fromLonLat([tsSiteInfo.lon, tsSiteInfo.lat]);
        } else {
            layerExtents = reprojectExtents(rawLayerExtents);
        }

        if (bandInfo === 'None') {
            cssStyles = 'Default';
        } else {
            cssStyles = {'color-map': {}};
            if (bandInfo.nd) {
                cssStyles['color-map'][bandInfo.nd] = {
                    color: '#000000',
                    opacity: 0
                };
            }
            cssStyles['color-map'][bandInfo.min] = {
                color: '#000000',
                opacity: 1
            };
            cssStyles['color-map'][bandInfo.max] = {
                color: '#ffffff',
                opacity: 1
            };
            if (bandInfo.min > 255 || bandInfo.max < 255) {
                hide255 = true;
            }
        }

        addLayerToMap({
            cssStyles: cssStyles,
            geomType: geomType,
            resType: resType,
            lyrExtents: layerExtents,
            url: projectInfo.map.geoserverUrl + '/wms',
            lyrId: layerId,
            hide255: hide255
        });

        layerIndex = layerCount.get();

        // Add layer data to project info
        projectInfo.map.layers[displayName] = {
            displayName: displayName,
            hsResId: resId,
            resType: resType,
            attributes: layerAttributes,
            cssStyles: cssStyles,
            extents: layerExtents,
            geomType: geomType,
            bandInfo: bandInfo,
            id: layerId,
            index: layerIndex,
            visible: true,
            hide255: hide255,
            listOrder: 1
        };

        createLayerListItem('prepend', layerIndex, layerId, resType, geomType, layerAttributes, true, displayName, bandInfo, resId);
        $newLayerListItem = $currentLayersList.find(':first-child');
        addListenersToListItem($newLayerListItem, layerIndex);
        addContextMenuToListItem($newLayerListItem, resType);

        drawLayersInListOrder(); // Must be called after creating the new layer list item
        zoomToLayer(layerExtents, map.getSize(), resType);

        if (isLastResource) {
            hideMainLoadAnim();
            showResLoadingStatus(true, 'Resource(s) added successfully!');
        }
    };

    addListenersToListItem = function ($listItem) {/*, layerIndex) {*/
        var $layerNameInput;
        $listItem.find('.layer-name').on('dblclick', function () {
            var $layerNameSpan = $(this);
            $layerNameSpan.addClass('hidden');
            $layerNameInput = $listItem.find('input[type=text]');
            $layerNameInput
                .removeClass('hidden')
                .select()
                .on('keyup', function (e) {
                    editLayerDisplayName(e, $(this), $layerNameSpan);/*, layerIndex);*/
                })
                .on('click', function (e) {
                    e.stopPropagation();
                });

            $(document).on('click.edtLyrNm', function () {
                closeLyrEdtInpt($layerNameSpan, $layerNameInput);
            });
        });
        $listItem.find('.hmbrgr-div img').on('click', function (e) {
            var clickedObj = $(e.currentTarget);
            var contextmenuId;
            var menuObj;
            var newStyle;
            contextmenuId = $listItem.attr('data-context-menu');
            menuObj = $('#' + contextmenuId);
            if (menuObj.attr('style') !== undefined && menuObj.attr('style').indexOf('display: none;') === -1) {
                window.setTimeout(function () {
                    newStyle = menuObj.attr('style').replace('inline-block', 'none');
                    menuObj.attr('style', newStyle);
                    clickedObj.parent().removeClass('hmbrgr-open');
                }, 50);
            }
        });
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
        $('#apply-opacity-to-colors').on('click', function () {
            var opacity = $('#raster-opacity').val();
            $('input[id^=color]').each(function (i, o) {
                var color = $(o).spectrum('get');
                color.setAlpha(opacity);
                $(o).spectrum('set', color);
            });
        });
        map.on('moveend', function () {
            $btnSaveProject.prop('disabled', false);
        });

        $('#close-modalViewFile').on('click', function () {
            $modalViewFile.modal('hide');
        });

        $modalLegend.on('shown.bs.modal', function () {
            $('#img-legend').css('height', $('#img-legend')[0].naturalHeight);
        });

        $btnSaveProject.on('click', function () {
            var resId = projectInfo.resId;
            if (resId === null) {
                $modalSaveNewProject.modal('show');
            } else {
                showMainLoadAnim();

                projectInfo.map.center = map.getView().getCenter();
                projectInfo.map.zoomLevel = map.getView().getZoom();

                $.ajax({
                    type: 'GET',
                    url: '/apps/hydroshare-gis/save-project',
                    dataType: 'json',
                    contentType: 'json',
                    data: {
                        res_id: resId,
                        project_info: JSON.stringify(projectInfo)
                    },
                    error: function () {
                        hideMainLoadAnim();
                        showResLoadingStatus(false, 'A problem occured while saving. Project not saved.');
                    },
                    success: function () {
                        hideMainLoadAnim();
                        showResLoadingStatus(true, 'Project saved successfully!');
                        $btnSaveProject.prop('disabled', true);
                    }
                });
            }
        });

        $('#btn-add-wms').on('click', function () {
            //http://geoserver.byu.edu/arcgis/rest/services/NWC/NWM_Geofabric/MapServer/export?bbox=-101589.77955203337,-1083684.5494424414,-51689.263084333936,-1043361.9687972802&layers=show:0,1,2
            var wmsUrl = $('#wms-url').val();
            var urlSplit = wmsUrl.split('/');
            var wmsName = urlSplit[urlSplit.indexOf('MapServer') - 1];
            var layerIndex;
            var $newLayerListItem;

            if (wmsUrl.indexOf('/rest/') > -1) {
                map.addLayer(new ol.layer.Tile({
                    source: new ol.source.TileArcGISRest({
                        url: wmsUrl
                    })
                }));
            } else {
                map.addLayer(new ol.layer.Tile({
                    source: new ol.source.TileWMS({
                        url: wmsUrl,
                        params: {
                            LAYERS: '0'
                        },
                        crossOrigin: 'Anonymous'
                    })
                }));
            }

            layerIndex = layerCount.get();

            createLayerListItem('prepend', layerIndex, wmsUrl, 'RasterResource', 'None', 'None', true, wmsName, 'None');
            $newLayerListItem = $currentLayersList.find(':first-child');
            addListenersToListItem($newLayerListItem, layerIndex);
            addContextMenuToListItem($newLayerListItem, 'RasterResource');

            drawLayersInListOrder(); // Must be called after creating the new layer list item
            $('#modalAddWMS').modal('hide');
            $('#wms-url').val('');
        });

        $('#btn-opt-add-to-new').on('click', function () {
            onClickAddToNewProject();
        });

        $('#btn-add-to-existing-project').on('click', function () {
            onClickAddToExistingProject();
        });

        $('#btn-opt-add-to-existing').on('click', function () {
            $('.opts-add-to-project').addClass('hidden');
            $('#opts-add-to-existing').toggleClass('hidden');
        });

        $btnSaveNewProject.on('click', onClickSaveNewProject);

        $btnShowModalSaveNewProject.on('click', function () {
            $modalSaveNewProject.modal('show');
        });

        $('#res-title').on('keyup', function () {
            $btnSaveNewProject.prop('disabled', $(this).val() === '');
        });

        $('.basemap-option').on('click', changeBaseMap);

        $modalLoadFile.on('hidden.bs.modal', function () {
            $('#input-files').val('');
        });

        $modalSaveNewProject.on('hidden.bs.modal', function () {
            $('#footer-info-saveProj').addClass('hidden');
            $('#res-title').val('');
        });

        $('#btn-upload-res').on('click', uploadResourceButtonHandler);

        $('#btn-upload-file').on('click', uploadFileButtonHandler);

        $('#input-files').on('change', function () {
            var files = this.files;
            if (!areValidFiles(files)) {
                $uploadBtn.prop('disabled', true);
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

            if ($(this).prop('checked') === true) {
                $('#outline-options').removeClass('hidden');
            } else {
                $('#outline-options').addClass('hidden');
            }

            if ($('#outline-options').hasClass('hidden')) {
                $('#symbology-preview').css('outline', '0');
            } else {
                color = $('#stroke').spectrum('get');
                if (color !== null) {
                    outlineString = $('#slct-stroke-width').val().toString();
                    outlineString += 'px solid ';
                    outlineString += color.toRgbString();
                    $('#symbology-preview').css('outline', outlineString);
                }
            }
        });

        $('#chkbx-include-labels').on('change', function () {
            if ($(this).prop('checked') === true) {
                $('#label-options').removeClass('hidden');
                $('#label-preview').removeClass('hidden');
            } else {
                $('#label-options').addClass('hidden');
                $('#label-preview').addClass('hidden');
            }
        });

        $('#geom-fill').spectrum({
            showInput: true,
            allowEmpty: false,
            showAlpha: true,
            showPalette: true,
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                var shape,
                    size,
                    geomType;

                if (color) {
                    color = color.toRgbString();
                    geomType = $btnApplySymbology.attr('data-geom-type');

                    if (geomType === 'point') {
                        shape = $('#slct-point-shape').val();
                        size = $('#slct-point-size').val();

                        drawPointSymbologyPreview(shape, size, color);
                    } else if (geomType === 'polygon') {
                        drawPointSymbologyPreview('square', 40, color);
                    }
                }
            }
        });

        $('#stroke').spectrum({
            showInput: true,
            allowEmpty: false,
            showAlpha: true,
            showPalette: true,
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                var outlineString;
                outlineString = $('#slct-stroke-width').val().toString();
                outlineString += 'px solid ';
                outlineString += color.toRgbString();
                $('#symbology-preview').css('outline', outlineString);
            }
        });

        $('#slct-stroke-width').on('change', function () {
            var outlineString;

            outlineString = $(this).val().toString();
            outlineString += 'px solid ';
            outlineString += $('#stroke').spectrum('get').toRgbString();
            $('#symbology-preview').css('outline', outlineString);
        });

        $('#font-fill').spectrum({
            showInput: true,
            allowEmpty: false,
            showAlpha: true,
            showPalette: true,
            color: 'black',
            chooseText: "Choose",
            cancelText: "Cancel",
            change: function (color) {
                if (color) {
                    $('#label-preview').css('color', color.toRgbString());
                }
            }
        });

        $('#slct-font-size').on('change', function () {
            $('#label-preview').css('font-size', $(this).val() + 'px');
        });

        $(window).on('resize', function () {
            $('#map').css({
                'height': $('#app-content').height(),
                'max-height': $('#app-content').height(),
                'width': '100%'
            });
            map.render();
        });

        $(window).on('webkitfullscreenchange mozfullscreenchange fullscreenchange', function () {
            if (window.innerHeight === screen.height) {
                $('#map').css({
                    'max-height': 'none',
                    'height': $(window).height(),
                    'width': $(window).width()
                });
            }
        });

        $btnApplySymbology.on('click', function () {
            updateSymbology($(this));
        });

        $('#slct-num-colors-in-gradient').on('change', function () {
            var i,
                inputSelector,
                htmlString = '',
                numColors = this.value,
                prevNumColors,
                createColorValPairHtml;

            createColorValPairHtml = function (j) {
                return '<fieldset class="color-val-pair">' +
                    '<label for="color' + j + '">Color:</label>' +
                    '<input type="text" id="color' + j + '">' +
                    '<label for="quantity' + j + '">Raster value:</label>' +
                    '<input type="text" id="quantity' + j + '">' +
                    '<br></fieldset>';
            };

            prevNumColors = $('.color-val-pair').length;
            i = prevNumColors;

            if (prevNumColors === undefined) {
                prevNumColors = 0;
                $('#color-map-placeholder').html();

                for (i = 0; i < numColors; i++) {
                    htmlString += createColorValPairHtml(i);
                }
            } else if (prevNumColors > numColors) {
                while (i > numColors) {
                    $('.color-val-pair').last().remove();
                    i--;
                }
            } else if (prevNumColors < numColors) {
                while (i < numColors) {
                    htmlString += createColorValPairHtml(i);
                    i++;
                }
            }

            $('#color-map-placeholder').attr('data-num-colors', numColors);

            if (htmlString !== '') {
                $('#color-map-placeholder').append(htmlString);
            }

            for (i = prevNumColors; i < numColors; i++) {
                inputSelector = '#color' + i;
                $(inputSelector).spectrum({
                    showInput: true,
                    allowEmpty: false,
                    showAlpha: true,
                    showPalette: true,
                    chooseText: "Choose",
                    cancelText: "Cancel"
                });
            }
            $('.color-val-pair').removeClass('hidden');
        });

        $('#slct-point-shape, #slct-point-size').on('change', function () {
            var shape,
                size,
                color;

            shape = $('#slct-point-shape').val();
            size = $('#slct-point-size').val();
            color = $('#geom-fill').spectrum('get').toRgbString();

            drawPointSymbologyPreview(shape, size, color);
        });

        $('#chkbx-show-inset-map').on('change', function () {
            if ($(this).is(':checked')) {
                projectInfo.map.showInset = true;
                insetMap = new ol.control.OverviewMap({
                    collapsed: false,
                    collapsible: false,
                    layers: [
                        new ol.layer.Tile({
                            style: 'Road',
                            source: new ol.source.BingMaps({
                                key: 'AnOW7YhvlSoT5teH6u7HmKhs2BJWeh5QNzp5CBU-4su1K1XI98TGIONClI22jpbk',
                                imagerySet: 'Road'
                            })
                        })
                    ]
                });
                map.addControl(insetMap);
            } else {
                projectInfo.map.showInset = false;
                map.removeControl(insetMap);
                insetMap = undefined;
            }
        });

        $('#btn-export-png').on('click', function () {
            if ($('#btn-export-png').prop('download') !== "") {
                map.once('postcompose', function (event) {
                    var canvas = createExportCanvas(event.context.canvas);
                    $(this).attr('href', canvas.toDataURL('image/png'));
                }, this);
                map.renderSync();
            } else {
                alert('This example requires a browser that supports the link download attribute.');
            }
        });

        $('#btn-export-pdf').on('click', function () {
            var dims = {
                a0: [1189, 841],
                a1: [841, 594],
                a2: [594, 420],
                a3: [420, 297],
                a4: [297, 210],
                a5: [210, 148]
            };
            var format = $('#slct-format').val();
            var dim = dims[format];

            $(this).prop('disabled', true);

            map.once('postcompose', function (event) {
                var canvas = createExportCanvas(event.context.canvas);
                var pdf = new jsPDF('landscape', undefined, format);
                var data = canvas.toDataURL('image/png');
                pdf.addImage(data, 'JPEG', 0, 0, dim[0], dim[1]);
                pdf.save('mapProject.pdf');
                $('#btn-export-pdf').prop('disabled', false);
            });
            map.renderSync();
        });

        (function () {
            var target, observer, config;
            // select the target node
            target = $('#app-content-wrapper')[0];

            observer = new MutationObserver(function () {
                window.setTimeout(function () {
                    map.updateSize();
                }, 500);
            });

            config = {attributes: true};

            observer.observe(target, config);
        }());
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
        return (((hasTif || hasZip) && fileCount === 1) || (hasShp && hasShx && hasPrj && hasDbf));
    };

    buildHSResTable = function (resList) {
        var resTableHtml;

        resList = typeof resList === 'string' ? JSON.parse(resList) : resList;
        resTableHtml = '<table id="tbl-resources"><thead><th></th><th>Title</th><th>Size</th><th>Type</th><th>Owner</th></thead><tbody>';

        resList.forEach(function (resource) {
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
    };

    changeBaseMap = function () {
        var selectedBaseMap = $(this).attr('value');

        $('.current-basemap-label').text('');
        $('.basemap-option').removeClass('selected-basemap-option');
        $(this).addClass('selected-basemap-option');
        $($(this).children()[0]).text(' (Current)');

        basemapLayers.forEach(function (layer) {
            layer.set('visible', (layer.get('style') === selectedBaseMap));
        });

        projectInfo.map.baseMap = selectedBaseMap;
        $btnSaveProject.prop('disabled', false);
    };

// Find if method is CSRF safe
    checkCsrfSafe = function (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    checkURLForParameters = function () {
        var transformToAssocArray,
            getSearchParameters,
            params;

        transformToAssocArray = function (prmstr) {
            var prms,
                prmArr,
                tmpArr;

            prmArr = prmstr.split("&");
            prms = {};

            prmArr.forEach(function (prm) {
                tmpArr = prm.split("=");
                prms[tmpArr[0]] = tmpArr[1];
            });

            return prms;
        };

        getSearchParameters = function () {
            var prmstr = window.location.search.substr(1);
            return (prmstr !== null && prmstr !== "") ? transformToAssocArray(prmstr) : {};
        };

        params = getSearchParameters();

        if (!(params.res_id === undefined || params.res_id === null)) {
            showMainLoadAnim();
            loadResource(params.res_id, null, null, true, null);
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

    createExportCanvas = function (mapCanvas) {
        var insetCanvas, exportCanvas, context, insetHeightOffset, $insetDiv, height, width,
            $insetMap, divHeightOffset, divWidthOffset;

        exportCanvas = $('#export-canvas')[0];
        exportCanvas.width = mapCanvas.width;
        exportCanvas.height = mapCanvas.height;
        context = exportCanvas.getContext('2d');
        context.drawImage(mapCanvas, 0, 0);
        $insetMap = $('.ol-overviewmap-map');
        if ($insetMap.length !== 0) {
            insetCanvas = $insetMap.find('canvas')[0];
            insetHeightOffset = mapCanvas.height - insetCanvas.height;
            context.drawImage(insetCanvas, 0, insetHeightOffset);
            $insetDiv = $('.ol-overlay-container');
            height = $insetDiv.height();
            width = $insetDiv.width();
            divHeightOffset = $insetDiv.position().top;
            divWidthOffset = $insetDiv.position().left;
            context.setLineDash([2, 2]);
            context.moveTo(divWidthOffset, insetHeightOffset + divHeightOffset);
            context.lineTo(divWidthOffset + width, insetHeightOffset + divHeightOffset);
            context.lineTo(divWidthOffset + width, insetHeightOffset + divHeightOffset + height);
            context.lineTo(divWidthOffset, insetHeightOffset + divHeightOffset + height);
            context.lineTo(divWidthOffset, insetHeightOffset + divHeightOffset);
            context.stroke();
        }
        return exportCanvas;
    };

    createLayerListItem = function (position, layerIndex, layerId, resType, geomType, layerAttributes, visible, layerName, bandInfo, resId, publicFilename, disableChkbx) {
        var $newLayerListItem;
        var chkbxHtml;
        if (disableChkbx === true) {
            chkbxHtml = '<input class="chkbx-layer" type="checkbox" disabled>';
        } else {
            chkbxHtml = '<input class="chkbx-layer" type="checkbox">';
        }
        var listHtmlString =
            '<li class="ui-state-default" ' +
            'data-layer-index="' + layerIndex + '" ' +
            'data-layer-id="' + layerId + '" ' +
            'data-res-id="' + resId + '" ' +
            'data-res-type="' + resType + '" ' +
            'data-geom-type="' + geomType + '" ' +
            'data-public-fname="' + publicFilename + '" ' +
            'data-layer-attributes="' + layerAttributes + '" ' +
            'data-band-min="' + (bandInfo ? bandInfo.min : undefined) + '" ' +
            'data-band-max="' + (bandInfo ? bandInfo.max : undefined) + '" ' +
            'data-band-nd="' + (bandInfo ? bandInfo.nd : undefined) + '">' +
            chkbxHtml +
            '<span class="layer-name">' + layerName + '</span>' +
            '<input type="text" class="edit-layer-name hidden" value="' + layerName + '">' +
            '<div class="hmbrgr-div"><img src="/static/hydroshare_gis/images/hamburger-menu.svg"></div>' +
            '</li>';

        if (position === 'prepend') {
            $currentLayersList.prepend(listHtmlString);
            $newLayerListItem = $currentLayersList.find(':first-child');
        } else {
            $currentLayersList.append(listHtmlString);
            $newLayerListItem = $currentLayersList.find(':last-child');
        }

        $newLayerListItem.find('.chkbx-layer').prop('checked', visible);
    };

    displaySymbologyModalError = function (errorString) {
        $('#symbology-modal-info')
            .text(errorString)
            .removeClass('hidden');
        setTimeout(function () {
            $('#symbology-modal-info').addClass('hidden');
        }, 7000);
    };

    deletePublicTempfiles = function () {
        $.ajax({
            url: '/apps/hydroshare-gis/delete-public-tempfiles',
            async: true
        });
    };

    drawLayersInListOrder = function () {
        var i,
            index,
            layer,
            displayName,
            numLayers,
            zIndex;

        numLayers = $currentLayersList.children().length + 2;
        for (i = 3; i <= numLayers; i++) {
            layer = $currentLayersList.find('li:nth-child(' + (i - 2) + ')');
            displayName = layer.find('.layer-name').text();
            index = Number(layer.attr('data-layer-index'));
            if (index < 1000) {
                zIndex = numLayers - i;
                map.getLayers().item(index).setZIndex(zIndex);
            }
            projectInfo.map.layers[displayName].listOrder = i - 2;
            $btnSaveProject.prop('disabled', false);
        }
    };

    drawPointSymbologyPreview = function (shape, size, color) {
        var cssObj = {},
            shapeStyleSheet = document.styleSheets[10],
            cssRule;

        $('#symbology-preview').text('');

        if (shapeStyleSheet.rules.length === 5) {
            shapeStyleSheet.deleteRule(4);
        } else if (shapeStyleSheet.rules.length === 6) {
            shapeStyleSheet.deleteRule(4);
            shapeStyleSheet.deleteRule(4);
        }

        if (shape === 'X') {
            cssObj = {
                'height': size + 'px',
                'width': size + 'px',
                'color': color,
                'font-size': size + 'px'
            };
            $('#symbology-preview').text('X');
        } else if (shape === 'triangle') {
            cssObj = {
                'border-left': Math.ceil(size / 2) + 'px solid transparent',
                'border-right': Math.ceil(size / 2) + 'px solid transparent',
                'border-bottom': size + 'px solid ' + color
            };
        } else if (shape === 'cross') {
            cssObj = {
                'height': size + 'px',
                'width': Math.ceil(size / 5) + 'px',
                'background-color': color
            };

            cssRule = '.cross:after {' +
                'background: ' + color + '; ' +
                'content: ""; ' +
                'height: ' + Math.ceil(size / 5) + 'px; ' +
                'left: -' + Math.ceil(size * 2 / 5) + 'px; ' +
                'position: absolute; ' +
                'top: ' + Math.ceil(size * 2 / 5) + 'px; ' +
                'width: ' + size + 'px;' +
                '}';

            shapeStyleSheet.insertRule(cssRule, 4);

        } else if (shape === 'star') {
            cssObj = {
                'border-right':  size + 'px solid transparent',
                'border-bottom': Math.ceil(size * 0.7) + 'px  solid ' + color,
                'border-left':   size + 'px solid transparent'
            };

            cssRule = '.star:before {' +
                'border-bottom: ' + Math.ceil(size * 0.8) + 'px solid ' + color + '; ' +
                'border-left: ' + Math.ceil(size * 0.3) + 'px solid transparent; ' +
                'border-right: ' + Math.ceil(size * 0.3) + 'px solid transparent;' +
                'position: absolute;' +
                'height: 0;' +
                'width: 0;' +
                'top: -' + Math.ceil(size * 0.45) + 'px;' +
                'left: -' + Math.ceil(size * 0.65) + 'px;' +
                'display: block;' +
                'content: ""; ' +
                '-webkit-transform: rotate(-35deg); ' +
                '-moz-transform: rotate(-35deg); ' +
                '-ms-transform: rotate(-35deg); ' +
                '-o-transform: rotate(-35deg);' +
                '}';

            shapeStyleSheet.insertRule(cssRule, 4);

            cssRule = '.star:after {' +
                'position: absolute;' +
                'display: block;' +
                'color: ' + color + ';' +
                'left: -' + Math.ceil(size * 1.05) + 'px;' +
                'width: 0;' +
                'height: 0;' +
                'border-right: ' + size + 'px solid transparent;' +
                'border-bottom: ' + Math.ceil(size * 0.7) + 'px  solid ' + color + ';' +
                'border-left: ' + size + 'px solid transparent;' +
                '-webkit-transform: rotate(-70deg);' +
                '-moz-transform: rotate(-70deg);' +
                '-ms-transform: rotate(-70deg);' +
                '-o-transform: rotate(-70deg);' +
                'content: "";' +
                '}';

            shapeStyleSheet.insertRule(cssRule, 5);

        } else {
            cssObj = {
                'height': size + 'px',
                'width': size + 'px',
                'background-color': color
            };
        }
        $('#symbology-preview')
            .removeClass()
            .addClass(shape)
            .removeAttr('style')
            .css(cssObj);
    };

    editLayerDisplayName = function (e, $layerNameInput, $layerNameSpan) {
        var newDisplayName;
        var nameB4Change = $layerNameSpan.text();
        if (e.which === 13) {  // Enter key
            newDisplayName = $layerNameInput.val();
            $layerNameSpan.text(newDisplayName);
            projectInfo.map.layers[nameB4Change].displayName = newDisplayName;
            projectInfo.map.layers[newDisplayName] = projectInfo.map.layers[nameB4Change];
            delete projectInfo.map.layers[nameB4Change];
            $btnSaveProject.prop('disabled', false);
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
                    featureProperties,
                    layerAttributesList = [],
                    dataTable,
                    tableHeadingHTML = '';

                if (response.hasOwnProperty('success')) {
                    featureProperties = JSON.parse(response.feature_properties);
                    layerAttributesList = layerAttributes.split(',');

                    layerAttributesList.forEach(function (attribute) {
                        tableHeadingHTML += '<th>' + attribute + '</th>';
                    });

                    attributeTableHTML = '<table id="tbl-attributes"><thead>' + tableHeadingHTML + '</thead><tbody>';

                    featureProperties.forEach(function (property) {
                        attributeTableHTML += '<tr>';
                        layerAttributesList.forEach(function (attribute) {
                            attributeTableHTML += '<td class="attribute" data-attribute="' + attribute + '">' + property[attribute] + '</td>';
                        });
                        attributeTableHTML += '</tr>';
                    });

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
            url: '/apps/hydroshare-gis/get-hs-res-list',
            dataType: 'json',
            error: function () {
                if (numRequests < 5) {
                    numRequests += 1;
                    setTimeout(generateResourceList, 3000, numRequests);
                } else {
                    $modalLoadRes.find('.modal-body').html('<div class="error">An unexpected error was encountered while attempting to load resorces.</div>');
                }
            },
            success: function (response) {
                if (response.hasOwnProperty('success')) {
                    if (!response.success) {
                        $modalLoadRes.find('.modal-body').html('<div class="error">' + response.message + '</div>');
                    } else {
                        if (response.hasOwnProperty('res_list')) {
                            buildHSResTable(response.res_list);
                        }
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

    getCssStyles = function (geomType) {
        var color,
            cssStyles = {};

        if (geomType === 'None') {
            cssStyles['color-map'] = {};
            (function () {
                var numColors,
                    i,
                    colorSelector,
                    opacity,
                    quantitySelector;

                numColors = $('#color-map-placeholder').attr('data-num-colors');
                for (i = 0; i < numColors; i++) {
                    colorSelector = '#color' + i;
                    quantitySelector = '#quantity' + i;
                    opacity = $(colorSelector).spectrum('get').getAlpha().toString();
                    cssStyles['color-map'][$(quantitySelector).val()] = {
                        'color': $(colorSelector).spectrum('get').toHexString(),
                        'opacity': opacity
                    };
                }
            }());
        } else {
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
                color = $('#stroke').spectrum('get');
                if (color !== null) {
                    cssStyles.stroke = color.toHexString();
                    cssStyles['stroke-opacity'] = color.getAlpha().toString();
                    cssStyles['stroke-width'] = $('#slct-stroke-width').val();
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
                    cssStyles['label-field'] = $('#slct-label-field').val();
                    cssStyles['font-size'] = $('#slct-font-size').val();
                    cssStyles['font-fill'] = color.toHexString();
                    cssStyles['font-fill-opacity'] = color.getAlpha().toString();
                } else {
                    displaySymbologyModalError('You must select a font color.');
                }
            }

            if (geomType === 'point') {
                cssStyles['point-shape'] = $('#slct-point-shape').val();
                cssStyles['point-size'] = $('#slct-point-size').val();
            }
        }

        return cssStyles;
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

    getGeoserverUrl = function () {
        $.ajax({
            url: '/apps/hydroshare-gis/get-geoserver-url',
            contentType: 'json',
            success: function (response) {
                if (response.hasOwnProperty('geoserver_url')) {
                    projectInfo.map.geoserverUrl = response.geoserver_url;
                } else {
                    alert('Function "getGeoserverUrl" has failed. The geoserver being used could not be identified.');
                }
            },
            error: function () {
                alert('Ajax request to "/apps/hydroshare-gis/get-geoserver-url" failed.');
            }
        });
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

    initializeJqueryVariables = function () {
        $btnShowModalSaveNewProject = $('#btn-show-modal-save-new-project');
        $btnApplySymbology = $('#btn-apply-symbology');
        $btnSaveNewProject = $('#btn-save-new-project');
        $btnSaveProject = $('#btn-save-project');
        $currentLayersList = $('#current-layers-list');
        $loadingAnimMain = $('#div-loading');
        $modalAttrTbl = $('#modalAttrTbl');
        $modalLegend = $('#modalLegend');
        $modalLoadFile = $('#modalLoadFile');
        $modalLoadRes = $('#modalLoadRes');
        $modalSaveNewProject = $('#modalSaveNewProject');
        $modalSymbology = $('#modalSymbology');
        $modalViewFile = $('#modalViewFile');
        $uploadBtn = $('.btn-upload');
    };

    initializeLayersContextMenus = function () {
        layersContextMenuBase = [
            {
                name: 'Open in HydroShare',
                title: 'Open in HydroShare',
                fun: function (e) {
                    onClickOpenInHS(e);
                }
            }, {
                name: 'Rename',
                title: 'Rename',
                fun: function (e) {
                    onClickRenameLayer(e);
                }
            }, {
                name: 'Delete',
                title: 'Delete',
                fun: function (e) {
                    onClickDeleteLayer(e);
                }
            }
        ];

        layersContextMenuViewFile = layersContextMenuBase.slice();
        layersContextMenuViewFile.unshift({
            name: 'View file',
            title: 'View file',
            fun: function (e) {
                onClickViewFile(e);
            }
        });

        layersContextMenuGeospatialBase = layersContextMenuBase.slice();
        layersContextMenuGeospatialBase.unshift({
            name: 'Zoom to',
            title: 'Zoom to',
            fun: function (e) {
                onClickZoomToLayer(e);
            }
        });

        layersContextMenuRaster = layersContextMenuGeospatialBase.slice();
        layersContextMenuRaster.unshift({
            name: 'Modify symbology',
            title: 'Modify symbology',
            fun: function (e) {
                onClickModifySymbology(e);
            }
        }, {
            name: 'View legend',
            title: 'View legend',
            fun: function (e) {
                onClickViewLegend(e);
            }
        });

        layersContextMenuVector = layersContextMenuRaster.slice();
        layersContextMenuVector.unshift({
            name: 'View attribute table',
            title: 'View attribute table',
            fun: function (e) {
                onClickShowAttrTable(e);
            }
        });

        layersContextMenuTimeSeries = layersContextMenuGeospatialBase.slice();
        layersContextMenuTimeSeries.unshift({
            name: 'View time series',
            title: 'View time series',
            fun: function (e) {
                var clickedElement = e.trigger.context,
                    $lyrListItem = $(clickedElement).parent().parent(),
                    resId = $lyrListItem.attr('data-layer-id');

                window.open('https://appsdev.hydroshare.org/apps/timeseries-viewer/?src=hydroshare&res_id=' + resId);
            }
        });

        contextMenuDict = {
            'GenericResource': layersContextMenuViewFile,
            'GeographicFeatureResource': layersContextMenuVector,
            'TimeSeriesResource': layersContextMenuTimeSeries,
            'RefTimeSeriesResource': layersContextMenuTimeSeries,
            'RasterResource': layersContextMenuRaster
        };
    };

    initializeMap = function () {
        var mousePositionControl = new ol.control.MousePosition({
                coordinateFormat: ol.coordinate.createStringXY(4),
                projection: 'EPSG:3857',
                className: 'custom-mouse-position',
                target: document.getElementById('mouse-position'),
                undefinedHTML: ''
            }),
            fullScreenControl = new ol.control.FullScreen();

        // Base Layer options
        basemapLayers = [
            new ol.layer.Tile({
                style: 'Aerial',
                visible: false,
                source: new ol.source.BingMaps({
                    key: 'AnOW7YhvlSoT5teH6u7HmKhs2BJWeh5QNzp5CBU-4su1K1XI98TGIONClI22jpbk',
                    imagerySet: 'Aerial'
                })
            }),
            new ol.layer.Tile({
                style: 'AerialWithLabels',
                visible: false,
                source: new ol.source.BingMaps({
                    key: 'AnOW7YhvlSoT5teH6u7HmKhs2BJWeh5QNzp5CBU-4su1K1XI98TGIONClI22jpbk',
                    imagerySet: 'AerialWithLabels'
                })
            }),
            new ol.layer.Tile({
                style: 'Road',
                visible: false,
                source: new ol.source.BingMaps({
                    key: 'AnOW7YhvlSoT5teH6u7HmKhs2BJWeh5QNzp5CBU-4su1K1XI98TGIONClI22jpbk',
                    imagerySet: 'Road'
                })
            })
        ];

        map = new ol.Map({
            layers: basemapLayers,
            target: 'map',
            view: new ol.View({
                center: [0, 0],
                zoom: 2,
                maxZoom: 19,
                minZoom: 2
            })
        });

        map.addControl(new ol.control.ZoomSlider());
        map.addControl(mousePositionControl);
        map.addControl(fullScreenControl);
    };

    loadProjectFile = function (fileProjectInfo) {
        var i,
            layers = fileProjectInfo.map.layers,
            numLayers = Object.keys(layers).length,
            key,
            layerIndex,
            downloadedGenericFiles = {},
            $newLayerListItem;

        projectInfo = fileProjectInfo;

        $('.basemap-option[value="' + fileProjectInfo.map.baseMap + '"]').trigger('click');

        for (i = 1; i <= numLayers; i++) {
            for (key in layers) {
                if (layers.hasOwnProperty(key)) {
                    if (layers[key].listOrder === i) {
                        if (layers[key].resType === 'RasterResource' || layers[key].resType === 'GeographicFeatureResource') {
                            addLayerToMap({
                                lyrExtents: layers[key].extents,
                                url: fileProjectInfo.map.geoserverUrl + '/wms',
                                lyrId: layers[key].id,
                                resType: layers[key].resType,
                                geomType: layers[key].geomType,
                                cssStyles: layers[key].cssStyles,
                                visible: layers[key].visible,
                                hide255: layers[key].hide255
                            });
                            layerIndex = layerCount.get();
                            createLayerListItem('append', layerIndex, layers[key].id, layers[key].resType,
                                layers[key].geomType, layers[key].attributes, layers[key].visible,
                                layers[key].displayName, layers[key].bandInfo, layers[key].hsResId);
                            $newLayerListItem = $currentLayersList.find(':last-child');
                            addListenersToListItem($newLayerListItem, layers[key].index);
                            addContextMenuToListItem($newLayerListItem, layers[key].resType);
                        } else if (layers[key].resType === 'GenericResource') {
                            if (!downloadedGenericFiles.hasOwnProperty(layers[key].hsResId)) {
                                $.ajax({
                                    type: 'GET',
                                    url: '/apps/hydroshare-gis/get-generic-files',
                                    data: {
                                        res_id: layers[key].hsResId
                                    },
                                    async: false,
                                    success: function (response) {
                                        if (response.hasOwnProperty('success')) {
                                            if (!response.success) {
                                                alert('Failed to obtain file from Generic resource');
                                            } else {
                                                (function (layers, key, layerIndex, $newLayerListItem) {
                                                    var res_files = response.results.res_files;
                                                    downloadedGenericFiles[layers[key].hsResId] = res_files;
                                                    if (res_files.indexOf(layers[key].filename) === -1) {
                                                        showResLoadingStatus(false, 'File named' + layers[key].filename + 'not found. Please check to make sure it was not renamed');
                                                    } else {
                                                        layerIndex = layers[key].index;
                                                        createLayerListItem('append', layerIndex, layers[key].id,
                                                            layers[key].resType, layers[key].geomType,
                                                            layers[key].attributes, true,
                                                            layers[key].displayName, layers[key].bandInfo,
                                                            layers[key].hsResId, layers[key].filename, true);
                                                        $newLayerListItem = $currentLayersList.find(':last-child');
                                                        addListenersToListItem($newLayerListItem, layers[key].index);
                                                        addContextMenuToListItem($newLayerListItem, layers[key].resType);
                                                    }
                                                }(layers, key, layerIndex, $newLayerListItem));
                                            }
                                        }
                                    }
                                });
                            } else {
                                if (downloadedGenericFiles[layers[key].hsResId].indexOf(layers[key].filename) === -1) {
                                    showResLoadingStatus(false, 'File named' + layers[key].filename + 'not found. Please check to make sure it was not renamed');
                                } else {
                                    layerIndex = layers[key].index;
                                    createLayerListItem('append', layerIndex, layers[key].id, layers[key].resType,
                                        layers[key].geomType, layers[key].attributes, true,
                                        layers[key].displayName, layers[key].bandInfo, layers[key].hsResId,
                                        layers[key].filename, true);
                                    $newLayerListItem = $currentLayersList.find(':last-child');
                                    addListenersToListItem($newLayerListItem, layers[key].index);
                                    addContextMenuToListItem($newLayerListItem, layers[key].resType);
                                }
                            }
                        }
                    }
                }
            }
        }
        drawLayersInListOrder();
        map.getView().setCenter(fileProjectInfo.map.center);
        map.getView().setZoom(fileProjectInfo.map.zoomLevel);

        $('#chkbx-show-inset-map').prop('checked', fileProjectInfo.map.showInset);
        $('#chkbx-show-inset-map').trigger('change');
        $('#load-from-pc').prop('disabled', false);
        window.setTimeout(function () {
            $btnSaveProject.prop('disabled', true);
        }, 100);
    };

    loadResource = function (resId, resType, resTitle, isLastResource, additionalResources) {
        var $footerInfoAddRes = $('#footer-info-addRes');
        var data = {'res_id': resId};

        if (resType) {
            data.res_type = resType;
        }
        if (resTitle) {
            data.res_title = resTitle;
        }

        $footerInfoAddRes.removeClass('hidden');

        $.ajax({
            type: 'GET',
            url: '/apps/hydroshare-gis/add-hs-res',
            dataType: 'json',
            data: data,
            error: function () {
                $footerInfoAddRes.addClass('hidden');
                $('#btn-upload-res').prop('disabled', false);
                console.error('Failure!');
            },
            success: function (response) {
                if (response.hasOwnProperty('success')) {
                    if (!response.success) {
                        showResLoadingStatus(false, response.message);
                        hideMainLoadAnim();
                    } else {
                        if (response.hasOwnProperty('results')) {
                            processAddHSResResults(response.results, isLastResource, additionalResources);
                        }
                        if ($('#chkbx-res-auto-close').is(':checked')) {
                            $modalLoadRes.modal('hide');
                        }
                    }
                }
                $footerInfoAddRes.addClass('hidden');
                $('#btn-upload-res').prop('disabled', false);
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

    onClickAddToExistingProject = function () {
        var $rdoSelectedProj,
            resId,
            resTitle,
            additionalResources;

        showMainLoadAnim();
        $('#modalAddToProject').modal('hide');

        $rdoSelectedProj = $('.opt-existing-project:checked');
        resId = $rdoSelectedProj.val();
        resTitle = $rdoSelectedProj.parent().text();
        additionalResources = [];
        $('#ul-resources-to-add').find('li').each(function (ignore, li) {
            var $li = $(li);
            additionalResources.push({
                'id': $li.attr('data-id'),
                'type': $li.attr('data-type'),
                'title': $li.attr('data-title')
            });
        });
        loadResource(resId, 'GenericResource', resTitle, false, additionalResources);
    };

    onClickAddToNewProject = function () {
        var additionalResources = [];
        var firstResource;

        showMainLoadAnim();
        $('#modalAddToProject').modal('hide');

        $('#ul-resources-to-add').find('li').each(function (ignore, li) {
            var $li = $(li);
            additionalResources.push({
                'id': $li.attr('data-id'),
                'type': $li.attr('data-type'),
                'title': $li.attr('data-title')
            });
        });
        firstResource = additionalResources.shift();
        loadResource(firstResource.id, firstResource.type, firstResource.title, (additionalResources.length === 0), additionalResources);
    };

    onClickDeleteLayer = function (e) {
        var clickedElement = e.trigger.context,
            count,
            $lyrListItem = $(clickedElement).parent().parent(),
            displayName = $lyrListItem.find('.layer-name').text(),
            deleteIndex = Number($lyrListItem.attr('data-layer-index')),
            i,
            index,
            // maxLyrIndxBfrDel,
            $layer;

        // var updateLayerIndex = function (startIndex, endIndex) {
        //     for (i = startIndex; i < endIndex; i++) {
        //         projectInfo.map.layers[i] = projectInfo.map.layers[i + 1];
        //         projectInfo.map.layers[i].index = i;
        //     }
        //     delete projectInfo.map.layers[endIndex];
        // };

        $lyrListItem.remove();
        delete projectInfo.map.layers[displayName];

        if (deleteIndex < 1000) {
            // maxLyrIndxBfrDel = layerCount.get();
            map.getLayers().removeAt(deleteIndex);
            // updateLayerIndex(deleteIndex, maxLyrIndxBfrDel);
        }

        count = $currentLayersList.children().length;
        for (i = 1; i <= count; i++) {
            $layer = $currentLayersList.find('li:nth-child(' + i + ')');
            displayName = $layer.find('.layer-name').text();
            index = Number($layer.attr('data-layer-index'));
            if (deleteIndex < 1000 && (index > deleteIndex)) {
                $layer.attr('data-layer-index', index - 1);
                projectInfo.map.layers[displayName].index = projectInfo.map.layers[displayName].index - 1;
            }
            projectInfo.map.layers[displayName].listOrder = i;
        }
    };

    onClickModifySymbology = function (e) {
        var clickedElement = e.trigger.context,
            $lyrListItem = $(clickedElement).parent().parent();

        setupSymbologyModalState($lyrListItem);
        $modalSymbology.modal('show');
    };

    onClickViewFile = function (e) {
        var clickedElement = e.trigger.context;
        var $lyrListItem = $(clickedElement).parent().parent();
        var fName = $lyrListItem.attr('data-public-fname');
        var url;
        var location = window.location;
        var obj;
        var done = false;
        var validImgTypes = ['png', 'jpg', 'gif'];

        $('.view-file').addClass('hidden');

        if (fName.toLowerCase().indexOf('.pdf') !== -1) {
            url = location.protocol + '//' + location.host + '/static/hydroshare_gis/ViewerJS/index.html#../temp/' + fName;
            $('#iframe-container')
                .empty()
                .append('<iframe id="iframe-js-viewer" src="' + url + '" allowfullscreen></iframe>')
                .removeClass('hidden');
            done = true;
        } else if (validImgTypes.indexOf(fName.toLowerCase().split('.')[1]) !== -1) {
            url = location.protocol + '//' + location.host + '/static/hydroshare_gis/temp/' + fName;
            obj = $('#img-viewer');
        } else {
            url = location.protocol + '//' + location.host + '/static/hydroshare_gis/temp/' + fName;
            obj = $('#unviewable-file');
            $('#link-download-file').attr('href', url);
        }
        if (!done) {
            obj.attr('src', url).removeClass('hidden');
        }
        $modalViewFile.modal('show');

        $(document).on('keyup.viewfile', function (e) {
            if (e.which === 27) {
                $(document).off('keyup.viewfile');
                $modalViewFile.modal('hide');
            }
        });
    };

    onClickOpenInHS = function (e) {
        var clickedElement = e.trigger.context;
        var $lyrListItem = $(clickedElement).parent().parent();
        var resId = $lyrListItem.attr('data-res-id');
        var urlBase;

        urlBase = 'https://www.hydroshare.org/resource/';
        window.open(urlBase + resId);
    };

    onClickRenameLayer = function (e) {
        var clickedElement = e.trigger.context,
            $lyrListItem = $(clickedElement).parent().parent(),
            $layerNameInput = $lyrListItem.find('input[type=text]'),
            $LayerNameSpan = $lyrListItem.find('span');
        // layerIndex = $lyrListItem.attr('data-layer-index');

        $LayerNameSpan.addClass('hidden');
        $lyrListItem.find('input')
            .removeClass('hidden')
            .select()
            .on('keyup', function (e) {
                editLayerDisplayName(e, $(this), $LayerNameSpan);/*, layerIndex);*/
            })
            .on('click', function (e) {
                e.stopPropagation();
            });

        $(document).on('click.edtLyrNm', function () {
            closeLyrEdtInpt($LayerNameSpan, $layerNameInput);
        });
    };

    onClickSaveNewProject = function () {
        var $footerInfoSaveProj = $('#footer-info-saveProj');

        $btnSaveProject.prop('disabled', true);
        $footerInfoSaveProj
            .html('Saving...<img src="/static/hydroshare_gis/images/loading-animation.gif" />')
            .removeClass('hidden error success');

        projectInfo.map.center = map.getView().getCenter();
        projectInfo.map.zoomLevel = map.getView().getZoom();

        $.ajax({
            type: 'GET',
            url: '/apps/hydroshare-gis/save-new-project',
            dataType: 'json',
            contentType: 'json',
            data: {
                'newResource': true,
                'projectInfo': JSON.stringify(projectInfo),
                'resTitle': $('#res-title').val(),
                'resAbstract': $('#res-abstract').val(),
                'resKeywords': $('#res-keywords').val()
            },
            error: function () {
                $footerInfoSaveProj
                    .addClass('error')
                    .html('An unexpected/unknown error occurred while attempting to save the project!');
                $btnSaveProject.prop('disabled', false);
            },
            success: processSaveNewProjectResponse
        });
    };

    onClickShowAttrTable = function (e) {
        showMainLoadAnim();
        var clickedElement = e.trigger.context,
            $lyrListItem = $(clickedElement).parent().parent(),
            layerName = $lyrListItem.text(),
            layerId = $lyrListItem.attr('data-layer-id'),
            layerAttributes = $lyrListItem.attr('data-layer-attributes');

        generateAttributeTable(layerId, layerAttributes, layerName);
    };

    onClickViewLegend = function (e) {
        var clickedElement = e.trigger.context;
        var $lyrListItem = $(clickedElement).parent().parent();
        var geomType = $lyrListItem.attr('data-geom-type');
        var layerId = $lyrListItem.attr('data-layer-id');
        var layerIndex = $lyrListItem.attr('data-layer-index');
        var layerName = $lyrListItem.text();
        var cssStyles = projectInfo.map.layers[layerIndex].cssStyles;
        var geoserverUrl = projectInfo.map.geoserverUrl;
        var imageUrl =  geoserverUrl + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=75&HEIGHT=75&LAYER=' + layerId;
        var hide255 = projectInfo.map.layers[layerIndex].hide255;

        imageUrl += '&LEGEND_OPTIONS=forceRule:True;fontStyle:bold;fontSize:14';
        if (cssStyles !== 'Default') {
            imageUrl += '&SLD_BODY=' + encodeURIComponent(SLD_TEMPLATES.getSldString(cssStyles, geomType, layerId, hide255, true));
        }
        $('#img-legend').attr('src', imageUrl);

        if (layerName.length >= 11) {
            layerName = layerName.slice(0, 11) + '...';
        }
        $modalLegend.find('.modal-title').text(layerName);
        $modalLegend.modal('show');
    };

    onClickZoomToLayer = function (e) {
        var clickedElement,
            index,
            layerExtent,
            resType,
            $lyrListItem;

        clickedElement = e.trigger.context;
        $lyrListItem = $(clickedElement).parent().parent();
        index = Number($lyrListItem.attr('data-layer-index'));
        resType = $lyrListItem.attr('data-res-type');
        if (resType.indexOf('TimeSeriesResource') > -1) {
            layerExtent = map.getLayers().item(3).getSource().getFeatures()[0].getGeometry().getCoordinates();
        } else {
            layerExtent = map.getLayers().item(index).getExtent();
        }

        zoomToLayer(layerExtent, map.getSize(), resType);
    };

    prepareFilesForAjax = function (files) {
        var data = new FormData();

        Object.keys(files).forEach(function (file) {
            data.append('files', files[file]);
        });

        return data;
    };

    processAddHSResResults = function (results, isLastResource, additionalResources) {
        var numResults = results.length;
        var result;
        var i;
        var numAdditionalResources;
        var resource;
        var j;
        for (i = 0; i < numResults; i++) {
            if (additionalResources) {
                numAdditionalResources = additionalResources.length;
                for (j = 0; j < numAdditionalResources; j++) {
                    resource = additionalResources[j];
                    loadResource(resource.id, resource.type, resource.title, (j === numAdditionalResources - 1), null);
                }
            }

            result = results[i];

            if (result.res_type === 'GenericResource') {
                if (result.project_info !== null) {
                    loadProjectFile(JSON.parse(result.project_info));
                    showResLoadingStatus(true, 'Project loaded successfully!');
                    hideMainLoadAnim();
                } else if (result.public_fname !== null) {
                    addGenericResToUI(result, isLastResource && i === numResults - 1);
                }
            } else {
                addLayerToUI(result, isLastResource && i === numResults - 1);
            }
        }
        $btnSaveProject.prop('disabled', false);
    };

    processSaveNewProjectResponse = function (response) {
        var $footerInfoSaveProj = $('#footer-info-saveProj');
        var resId;
        if (response.hasOwnProperty('success')) {
            if (response.success) {
                resId = response.res_id;
                projectInfo.resId = resId;
                $footerInfoSaveProj
                    .addClass('success')
                    .html('Save successful. Access resource <a target="_blank" href="https://www.hydroshare.org/resource/' + resId + '">here</a>.');
                $('#load-from-pc').prop('disabled', false);
            } else {
                $footerInfoSaveProj
                    .addClass('error')
                    .html(response.message);
            }
        }
        $btnSaveProject.prop('disabled', true);
    };

    redrawDataTable = function (dataTable, $modal) {
        var interval;
        interval = window.setInterval(function () {
            if ($modal.css('display') !== 'none' && $modal.find('table').length > 0) {
                $modal.find('.dataTables_scrollBody').css('height', $modal.find('.modal-body').height().toString() - 160 + 'px');
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

    setupSymbologyLabelsState = function (layerCssStyles) {
        var color;

        $('#chkbx-include-labels')
            .prop('checked', true)
            .trigger('change');
        $('#label-field').val(layerCssStyles['label-field']);
        $('#slct-font-size').val(layerCssStyles['font-size']);
        color = tinycolor(layerCssStyles['font-fill']);
        color.setAlpha(layerCssStyles['font-fill-opacity']);
        $('#font-fill').spectrum('set', color);
    };

    setupSymbologyModalState = function ($lyrListItem) {
        var geomType = $lyrListItem.attr('data-geom-type'),
            layerId = $lyrListItem.attr('data-layer-id'),
            layerIndex = $lyrListItem.attr('data-layer-index'),
            labelFieldOptions = $lyrListItem.attr('data-layer-attributes').split(','),
            bandInfo = {
                'min': $lyrListItem.attr('data-band-min'),
                'max': $lyrListItem.attr('data-band-max'),
                'nd': $lyrListItem.attr('data-band-nd')
            },
            optionsHtmlString = '',
            layerCssStyles;

        $modalSymbology.find('.modal-title').text('Modify Symbology for: ' + $lyrListItem.find('.layer-name').text());
        $modalSymbology.find('#btn-apply-symbology').attr({
            'data-geom-type': geomType,
            'data-layer-id': layerId,
            'data-layer-index': layerIndex
        });

        labelFieldOptions.forEach(function (option) {
            optionsHtmlString += '<option value="' + option + '">' + option + '</option>';
        });
        $('#slct-label-field').html(optionsHtmlString);

        $modalSymbology.find('fieldset').addClass('hidden');
        $('#symbology-preview-container').addClass('hidden');
        $('#chkbx-include-outline')
            .prop('checked', false)
            .trigger('change');
        $('#chkbx-include-labels')
            .prop('checked', false)
            .trigger('change');

        layerCssStyles = projectInfo.map.layers[layerIndex].cssStyles;
        if (geomType === 'polygon') {
            setupSymbologyPolygonState(layerCssStyles);
        } else if (geomType === 'point') {
            setupSymbologyPointState(layerCssStyles);
        } else if (geomType === 'line') {
            setupSymbologyPolylineState(layerCssStyles);
        } else if (geomType === 'None') {
            setupSymbologyRasterState(layerCssStyles, bandInfo);
        }
    };

    setupSymbologyPointState = function (layerCssStyles) {
        var color;
        var shape;
        var size;

        if (layerCssStyles === "Default") {
            $('#slct-point-shape').val('square');
            $('#slct-point-size').val(6);
            $('#geom-fill').spectrum('set', '#FF0000');
            $('#symbology-preview')
                .removeClass()
                .css({
                    'height': '6px',
                    'width': '6px',
                    'background-color': '#FF0000'
                });
        } else {
            shape = layerCssStyles['point-shape'];
            size = layerCssStyles['point-size'];
            color = tinycolor(layerCssStyles.fill);
            color.setAlpha(layerCssStyles['fill-opacity']);

            $('#slct-point-shape').val(shape);
            $('#slct-point-size').val(size);
            $('#geom-fill').spectrum('set', color);
            drawPointSymbologyPreview(shape, size, color.toRgbString());

            if (Number(layerCssStyles['stroke-opacity'] > 0)) {
                setupSymbologyStrokeState(layerCssStyles);
            }

            if (layerCssStyles.labels) {
                setupSymbologyLabelsState(layerCssStyles);
            }
        }
        $('.point').removeClass('hidden');
        $('#symbology-preview-container').removeClass('hidden');
    };

    setupSymbologyPolygonState = function (layerCssStyles) {
        var color;

        $('#symbology-preview')
            .removeClass()
            .css({
                'height': '40px',
                'width': '40px'
            });

        if (layerCssStyles === "Default") {
            $('#geom-fill').spectrum('set', '#AAAAAA');
            $('#symbology-preview').css('background-color', '#AAAAAA');
            $('#stroke').spectrum('set', '#000000');
            $('#slct-stroke-width').val(1);
            $('#chkbx-include-outline')
                .prop('checked', true)
                .trigger('change');
        } else {
            color = tinycolor(layerCssStyles.fill);
            color.setAlpha(layerCssStyles['fill-opacity']);
            $('#geom-fill').spectrum('set', color);
            $('#symbology-preview').css('background-color', color.toRgbString());

            if (Number(layerCssStyles['stroke-opacity'] > 0)) {
                setupSymbologyStrokeState(layerCssStyles);
            }

            if (layerCssStyles.labels) {
                setupSymbologyLabelsState(layerCssStyles);
            }
        }

        $('.polygon').removeClass('hidden');
        $('#symbology-preview-container').removeClass('hidden');
    };

    setupSymbologyPolylineState = function (layerCssStyles) {
        if (layerCssStyles === "Default") {
            $('#stroke').spectrum('set', '#0000FF');
            $('#slct-stroke-width').val(1);
        } else {
            setupSymbologyStrokeState(layerCssStyles);

            if (layerCssStyles.labels) {
                setupSymbologyLabelsState(layerCssStyles);
            }
        }
        $('.line').removeClass('hidden');
        $('#symbology-preview-container').removeClass('hidden');
    };

    setupSymbologyRasterState = function (layerCssStyles, bandInfo) {
        var colorKeys,
            color,
            numKeys,
            colorMapObj,
            i,
            quantitySelector,
            colorSelector;

        if (layerCssStyles === "Default") {
            $('#slct-num-colors-in-gradient').trigger('change');
        } else {
            colorMapObj = layerCssStyles['color-map'];
            colorKeys = Object.keys(colorMapObj).sort(function (a, b) {return Number(a) - Number(b); });
            numKeys = colorKeys.length;
            $('#slct-num-colors-in-gradient')
                .val(numKeys)
                .trigger('change');

            i = 0;
            colorKeys.forEach(function (quantity) {
                quantitySelector = '#quantity' + i;
                colorSelector = '#color' + i;
                $(quantitySelector).val(quantity);
                color = tinycolor(colorMapObj[quantity].color);
                color.setAlpha(colorMapObj[quantity].opacity);
                $(colorSelector).spectrum('set', color);
                i += 1;
            });
        }

        $('#rast-min-val').text(bandInfo.min);
        $('#rast-max-val').text(bandInfo.max);
        $('#rast-nd-val').text(bandInfo.nd);
        $('.raster').removeClass('hidden');
    };

    setupSymbologyStrokeState = function (layerCssStyles) {
        var color;

        $('#chkbx-include-outline')
            .prop('checked', true)
            .trigger('change');
        color = tinycolor(layerCssStyles.stroke);
        color.setAlpha(layerCssStyles['stroke-opacity']);
        $('#stroke').spectrum('set', color);
        $('#slct-stroke-width').val(layerCssStyles['stroke-width']);
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

    showResLoadingStatus = function (success, message) {
        var successClass = success ? 'success' : 'error';
        var $resLoadingStatus = $('#res-load-status');
        var $statusText = $('#status-text');
        var showTime = success ? 2000 : 4000;
        $statusText.text(message)
            .removeClass('success error')
            .addClass(successClass);
        $resLoadingStatus.removeClass('hidden');
        setTimeout(function () {
            $resLoadingStatus.addClass('hidden');
        }, showTime);
    };

    updateSymbology = function ($this) {
        var geomType = $this.attr('data-geom-type'),
            layerId = $this.attr('data-layer-id'),
            layerIndex = $this.attr('data-layer-index'),
            sldString,
            cssStyles,
            hide255 = projectInfo.map.layers[layerIndex].hide255;

        cssStyles = getCssStyles(geomType);
        if (cssStyles === null) {
            return;
        }
        projectInfo.map.layers[layerIndex].cssStyles = cssStyles;
        sldString = SLD_TEMPLATES.getSldString(cssStyles, geomType, layerId, hide255);

        map.getLayers().item(layerIndex).getSource().updateParams({'SLD_BODY': sldString});
    };

    uploadFileButtonHandler = function () {
        var files = $('#input-files')[0].files,
            data,
            $footerInfoAddFile = $('#footer-info-addFile');

        $footerInfoAddFile.removeClass('hidden');
        $uploadBtn.prop('disabled', true);
        showMainLoadAnim();
        data = prepareFilesForAjax(files);
        data.append('proj_id', projectInfo.resId);

        $.ajax({
            url: '/apps/hydroshare-gis/add-local-file/',
            type: 'POST',
            data: data,
            dataType: 'json',
            processData: false,
            contentType: false,
            error: function (ignore1, textStatus, ignore2) {
                $footerInfoAddFile.addClass('hidden');
                showResLoadingStatus('error', textStatus);
            },
            success: function (response) {
                $footerInfoAddFile.addClass('hidden');
                $('#btn-upload-file').prop('disabled', false);
                if (response.hasOwnProperty('success')) {
                    if (response.success) {
                        addLayerToUI(response.results, true);
                        $btnSaveProject.prop('disabled', false);
                    }
                }
                if ($('#chkbx-file-auto-close').is(':checked')) {
                    $modalLoadFile.modal('hide');
                }
            }
        });
    };

    uploadResourceButtonHandler = function () {

        $uploadBtn.prop('disabled', true);
        var $rdoRes = $('.rdo-res:checked'),
            resId = $rdoRes.val(),
            resType = $rdoRes.parent().parent().find('.res_type').text(),
            resTitle = $rdoRes.parent().parent().find('.res_title').text();

        showMainLoadAnim();
        loadResource(resId, resType, resTitle, true, null);
    };

    zoomToLayer = function (layerExtent, mapSize, resType) {
        if (resType.indexOf('TimeSeriesResource') > -1) {
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
        $('#app-content, #inner-app-content').css('max-height', $(window).height() - 100);
        $('#map').css({
            'height': $('#app-content').height(),
            'max-height': $('#app-content').height()
        });
        initializeJqueryVariables();
        checkURLForParameters();
        addDefaultBehaviorToAjax();
        initializeMap();
        initializeLayersContextMenus();
        addInitialEventListeners();

        $currentLayersList.sortable({
            placeholder: "ui-state-highlight",
            stop: drawLayersInListOrder
        });
        $currentLayersList.disableSelection();
    });

    if (window.location.pathname.indexOf('add-to-project') > -1) {
        $('#modalAddToProject').modal('show');
    } else {
        $('#modalWelcome').modal('show');
    }

    /*-----------------------------------------------
     ***************INVOKE IMMEDIATELY***************
     ----------------------------------------------*/
    projectInfo = {
        'resId': null,
        'map': {
            'baseMap': 'None',
            'showInset': false,
            'layers': {},
            'zoomLevel': 2,
            'center': [0, 0],
            'geoserverUrl': null
        }
    };

    getGeoserverUrl();

    generateResourceList();

    layerCount = (function () {
        // The count = 2 (0-based) accounts for the 3 base maps added before this count is initialized
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

    window.onbeforeunload = deletePublicTempfiles;
}());