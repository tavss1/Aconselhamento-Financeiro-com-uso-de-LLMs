import React, { useState } from 'react';
import { Upload } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { dashboardService } from '../../services/dashboardService';

export const ExtractUpload = ({ onUploadComplete }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const { token } = useAuth();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'text/csv') {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Por favor, selecione um arquivo CSV válido');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');

    try {
      const result = await dashboardService.uploadExtract(file, token);
      onUploadComplete(result);
    } catch (error) {
      setError(error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <Upload className="h-16 w-16 text-blue-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Upload do Extrato Bancário
          </h2>
          <p className="text-gray-600">
            Envie seu extrato em formato CSV para análise personalizada
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Selecionar Arquivo CSV
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">
              {error}
            </div>
          )}

          {file && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>Arquivo selecionado:</strong> {file.name}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Tamanho: {(file.size / 1024).toFixed(2)} KB
              </p>
            </div>
          )}

          <div className="bg-blue-50 p-4 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Formato do CSV:</h4>
            <p className="text-sm text-blue-700">
              O arquivo deve conter as colunas: <strong>data, descricao, valor</strong>
            </p>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Enviando...' : 'Fazer Upload'}
          </button>
        </div>
      </div>
    </div>
  );
};