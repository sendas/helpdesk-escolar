<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5">Categorias</div>
      <q-space />
      <q-btn color="primary" icon="add" label="Nova Categoria" @click="showDialog = true" />
    </div>

    <q-card>
      <q-table :rows="categories" :columns="columns" row-key="id" :loading="loading" flat>
        <template #body-cell-color="props">
          <q-td :props="props">
            <div :style="`background:${props.value}; width:24px; height:24px; border-radius:4px;`" />
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn flat dense icon="delete" color="negative" @click="onDelete(props.row)" />
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- Create dialog -->
    <q-dialog v-model="showDialog">
      <q-card style="min-width:340px">
        <q-card-section class="text-h6">Nova Categoria</q-card-section>
        <q-separator />
        <q-card-section>
          <q-form @submit.prevent="onCreate" class="q-gutter-sm">
            <q-input v-model="form.name" label="Nome *" outlined :rules="[(v) => !!v || 'Obrigatório']" />
            <q-input v-model="form.description" label="Descrição" outlined />
            <q-input v-model="form.color" label="Cor (hex)" outlined>
              <template #append>
                <div :style="`background:${form.color}; width:20px; height:20px; border-radius:4px`" />
              </template>
            </q-input>
            <div class="row justify-end q-mt-sm">
              <q-btn flat label="Cancelar" v-close-popup />
              <q-btn type="submit" label="Criar" color="primary" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Notify, Dialog } from 'quasar'
import { getCategories, createCategory, deleteCategory } from '../../api/tickets'

const categories = ref<any[]>([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const form = ref({ name: '', description: '', color: '#1976D2' })

const columns: any[] = [
  { name: 'id', label: '#', field: 'id', align: 'left', style: 'width:60px' },
  { name: 'color', label: 'Cor', field: 'color', align: 'left', style: 'width:60px' },
  { name: 'name', label: 'Nome', field: 'name', align: 'left' },
  { name: 'description', label: 'Descrição', field: 'description', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'center' },
]

onMounted(load)

async function load() {
  loading.value = true
  try {
    categories.value = await getCategories()
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  saving.value = true
  try {
    await createCategory(form.value)
    showDialog.value = false
    form.value = { name: '', description: '', color: '#1976D2' }
    Notify.create({ type: 'positive', message: 'Categoria criada' })
    await load()
  } catch (e: any) {
    Notify.create({ type: 'negative', message: e?.response?.data?.detail || 'Erro ao criar categoria' })
  } finally {
    saving.value = false
  }
}

function onDelete(cat: any) {
  Dialog.create({
    title: 'Confirmar',
    message: `Eliminar a categoria "${cat.name}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await deleteCategory(cat.id)
      Notify.create({ type: 'positive', message: 'Categoria eliminada' })
      await load()
    } catch {
      Notify.create({ type: 'negative', message: 'Erro ao eliminar' })
    }
  })
}
</script>
